"""
Cubox 同步服务

从 web 路由中抽取的同步逻辑，供 API 端点与定时调度器共用。
"""

from datetime import datetime
from typing import List

from rich.console import Console

from src.config import get_config_manager

console = Console()


def run_sync(incremental: bool = False) -> dict:
    """执行 Cubox 同步

    Args:
        incremental: 是否增量同步（基于上次同步时间）

    Returns:
        同步结果字典（status/message/count/wechat_enqueued）

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

    # 同步后自动入队微信文章下载（配置启用时）
    wechat_enqueued = 0
    try:
        wechat_config = get_config_manager().load_config().wechat
        if wechat_config.enabled and wechat_config.download_on_sync:
            from src.services.wechat_queue import enqueue_wechat_articles
            wechat_enqueued = enqueue_wechat_articles(articles)
    except Exception as e:
        # 入队失败不影响同步结果
        console.print(f"[yellow]微信文章入队失败: {e}[/yellow]")

    return {
        "status": "ok",
        "message": f"同步完成，获取 {len(articles)} 篇文章",
        "count": len(articles),
        "wechat_enqueued": wechat_enqueued,
    }
