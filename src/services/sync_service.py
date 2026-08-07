"""
Cubox 同步服务

从 web 路由中抽取的同步逻辑，供 API 端点与定时调度器共用。
"""

import threading
from datetime import datetime
from typing import Optional

from rich.console import Console

console = Console()

# 全局同步状态
_sync_status = {
    "running": False,
    "progress": "",
    "total": 0,
    "processed": 0,
    "error": None,
    "last_sync_time": None,
    "should_cancel": False,  # 取消标志
}
_sync_lock = threading.Lock()


def get_sync_status() -> dict:
    """获取当前同步状态"""
    with _sync_lock:
        return {
            "running": _sync_status["running"],
            "progress": _sync_status["progress"],
            "total": _sync_status["total"],
            "processed": _sync_status["processed"],
            "error": _sync_status["error"],
            "last_sync_time": _sync_status["last_sync_time"],
        }


def cancel_sync() -> dict:
    """取消正在运行的同步任务"""
    with _sync_lock:
        if not _sync_status["running"]:
            return {"status": "error", "message": "没有正在运行的同步任务"}
        _sync_status["should_cancel"] = True
        return {"status": "ok", "message": "正在取消同步..."}


def _should_cancel() -> bool:
    """检查是否应该取消同步"""
    with _sync_lock:
        return _sync_status["should_cancel"]


def _update_sync_status(running: bool = None, progress: str = None,
                        total: int = None, processed: int = None,
                        error: str = None, last_sync_time: str = None):
    """更新同步状态"""
    with _sync_lock:
        if running is not None:
            _sync_status["running"] = running
            if running:
                # 开始新任务时重置取消标志
                _sync_status["should_cancel"] = False
        if progress is not None:
            _sync_status["progress"] = progress
        if total is not None:
            _sync_status["total"] = total
        if processed is not None:
            _sync_status["processed"] = processed
        if error is not None:
            _sync_status["error"] = error
        if last_sync_time is not None:
            _sync_status["last_sync_time"] = last_sync_time


def _do_sync(incremental: bool = False):
    """执行实际的同步操作（由 _do_sync_wrapper 或 run_sync(background=False) 调用）"""
    try:
        _update_sync_status(progress="初始化...", total=0, processed=0, error=None)

        from src.adapters.cubox_adapter import CuboxAdapter
        from src.models import SourceConfig

        # 创建适配器并传入进度回调
        adapter = CuboxAdapter(use_sqlite=True, progress_callback=_update_progress)
        source_config = SourceConfig(
            type="cubox",
            name="Cubox 收藏",
            identifier="cubox-cli",
            enabled=True,
        )

        if not adapter.validate(source_config):
            _update_sync_status(running=False, error="Cubox CLI 不可用")
            return

        _update_sync_status(progress="正在获取文章列表...")

        if incremental:
            # 从上次同步状态推断增量起点
            state = adapter.get_state(source_config)
            since = 0.0
            last_sync = state.get("last_sync")
            if last_sync:
                try:
                    since = datetime.fromisoformat(last_sync).timestamp()
                except Exception:
                    since = 0.0
            articles = adapter.fetch_incremental(source_config, since=since)
        else:
            articles = adapter.fetch(source_config)

        _update_sync_status(
            progress=f"同步完成，获取 {len(articles)} 篇文章",
            total=len(articles),
            processed=len(articles),
            last_sync_time=datetime.now().isoformat(),
        )

    except InterruptedError as e:
        # 用户取消（running 由调用方恢复）
        _update_sync_status(error=str(e))
        console.print(f"[yellow]同步已取消[/yellow]")
    except Exception as e:
        import traceback
        traceback.print_exc()
        _update_sync_status(error=str(e))
        console.print(f"[red]同步失败: {e}[/red]")


def _update_progress(total: int, processed: int, message: str = ""):
    """进度回调函数，供 CuboxAdapter 调用"""
    _update_sync_status(total=total, processed=processed, progress=message or f"处理中... {processed}/{total}")

    # 检查是否应该取消
    if _should_cancel():
        raise InterruptedError("同步已被用户取消")


def run_sync(incremental: bool = False, background: bool = True) -> dict:
    """启动 Cubox 同步（含完整正文、批注、AI 洞见）

    Args:
        incremental: 是否增量同步（基于上次同步时间）
        background: 是否在后台执行（默认 True）

    Returns:
        同步结果字典（status/message）

    Raises:
        ValueError: Cubox CLI 不可用或已有同步任务运行中
    """
    # 原子操作：在同一锁区间内检查 + 设置 running，消除并发空窗
    with _sync_lock:
        if _sync_status["running"]:
            raise ValueError("已有同步任务正在运行")
        _sync_status["running"] = True
        _sync_status["should_cancel"] = False
        _sync_status["error"] = None
        _sync_status["progress"] = "初始化..."

    if background:
        thread = threading.Thread(target=_do_sync_wrapper, args=(incremental,), daemon=True)
        thread.start()
        return {
            "status": "started",
            "message": "同步任务已启动，请查询同步状态",
        }
    else:
        try:
            _do_sync(incremental)
        finally:
            with _sync_lock:
                _sync_status["running"] = False
        status = get_sync_status()
        if status["error"]:
            raise Exception(status["error"])
        return {
            "status": "ok",
            "message": status["progress"],
            "count": status["total"],
        }


def _do_sync_wrapper(incremental: bool):
    """后台线程包装器，确保 running 状态最终恢复"""
    try:
        _do_sync(incremental)
    finally:
        with _sync_lock:
            _sync_status["running"] = False


def backfill_content(limit: int = 0) -> dict:
    """为已有 Cubox 文章补抓完整正文

    Args:
        limit: 最多处理篇数（0=不限制）

    Returns:
        结果字典
    """
    from src.adapters.cubox_adapter import CuboxAdapter
    from src.models import SourceConfig

    adapter = CuboxAdapter(use_sqlite=True)
    source_config = SourceConfig(
        type="cubox",
        name="Cubox 收藏",
        identifier="cubox-cli",
        enabled=True,
    )

    if not adapter.validate(source_config):
        raise ValueError("Cubox CLI 不可用")

    count = adapter.backfill_full_content(source_config, limit=limit)
    return {
        "status": "ok",
        "message": f"补抓完成，更新 {count} 篇文章",
        "count": count,
    }
