"""
Cubox 同步服务

从 web 路由中抽取的同步逻辑，供 API 端点与定时调度器共用。
"""

from datetime import datetime

from rich.console import Console

console = Console()


def run_sync(incremental: bool = False) -> dict:
    """执行 Cubox 同步（含完整正文、批注、AI 洞见）

    Args:
        incremental: 是否增量同步（基于上次同步时间）

    Returns:
        同步结果字典（status/message/count）

    Raises:
        ValueError: Cubox CLI 不可用
        Exception: 同步过程出错
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

    return {
        "status": "ok",
        "message": f"同步完成，获取 {len(articles)} 篇文章（含完整正文）",
        "count": len(articles),
    }


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
