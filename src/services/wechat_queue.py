"""
微信文章下载队列

单 worker 线程 + threading.Event 唤醒机制。
限速由 wechat_downloader.download() 内的令牌桶统一执行，
队列 worker 与单篇下载端点天然共用同一限速。

不在 import 时启动 worker，由 app lifespan 显式调用 start_worker()。
"""

import threading
import traceback
from typing import Dict, List, Optional

from rich.console import Console

from src.models import Article
from src.storage import get_storage

console = Console()

# 微信文章 URL 特征
WECHAT_URL_KEYWORD = "mp.weixin.qq.com"

_worker_thread: Optional[threading.Thread] = None
_wake_event = threading.Event()
_current_lock = threading.Lock()
_current: Dict = {"article_id": None, "title": None}


def enqueue_wechat_articles(articles: List[Article]) -> int:
    """把微信文章登记入队并唤醒 worker，返回新登记数量"""
    items = [
        {"article_id": a.id, "url": a.url}
        for a in articles
        if a.url and WECHAT_URL_KEYWORD in a.url
    ]
    if not items:
        return 0
    # INSERT OR IGNORE，天然幂等
    inserted = get_storage().enqueue_downloads(items)
    if inserted:
        _wake_event.set()
    return inserted


def scan_and_enqueue_pending() -> int:
    """扫描库中所有微信文章，未登记过的入队，返回新登记数量"""
    storage = get_storage()
    articles = storage.get_articles_by_url_like(WECHAT_URL_KEYWORD)
    return enqueue_wechat_articles(articles)


def _set_current(article_id: Optional[str], title: Optional[str]):
    """更新当前处理状态"""
    with _current_lock:
        _current["article_id"] = article_id
        _current["title"] = title


def _worker_loop():
    """worker 主循环：逐条消费 pending 任务，队列为空则阻塞等唤醒"""
    from src.services.wechat_downloader import WeChatDownloader

    storage = get_storage()
    downloader = WeChatDownloader()

    while True:
        pending = storage.get_pending_downloads(limit=1)
        if not pending:
            _wake_event.wait(timeout=60)
            _wake_event.clear()
            continue

        item = pending[0]
        article_id = item["article_id"]
        storage.update_download_status(article_id, "downloading")
        _set_current(article_id, None)

        try:
            article = storage.get_article(article_id)
            if not article:
                storage.update_download_status(article_id, "failed", error="文章不存在")
                continue
            _set_current(article_id, article.title)

            # 限速在 downloader.download() 内按 requests_per_minute 执行
            files = downloader.process_article(article)
            storage.update_download_status(article_id, "done", files=files)
            console.print(f"[green]✓ 微信文章下载完成: {article.title[:40]}[/green]")
        except Exception as e:
            console.print(f"[red]微信文章下载失败 [{article_id}]: {e}[/red]")
            traceback.print_exc()
            storage.update_download_status(article_id, "failed", error=str(e))
        finally:
            _set_current(None, None)


def start_worker():
    """启动下载 worker（幂等）

    先将崩溃残留的 downloading 重置为 pending（断点恢复），再启动 daemon 线程。
    """
    global _worker_thread
    if _worker_thread and _worker_thread.is_alive():
        return

    reset = get_storage().reset_downloading_to_pending()
    if reset:
        console.print(f"[yellow]恢复 {reset} 条中断的微信下载任务[/yellow]")

    _worker_thread = threading.Thread(
        target=_worker_loop, daemon=True, name="wechat-download-worker"
    )
    _worker_thread.start()
    console.print("[green]微信下载 worker 已启动[/green]")


def get_current() -> Dict:
    """获取当前处理状态与 worker 存活情况"""
    with _current_lock:
        return {
            "article_id": _current["article_id"],
            "title": _current["title"],
            "worker_alive": bool(_worker_thread and _worker_thread.is_alive()),
        }


def wake_worker():
    """唤醒 worker（如 retry-failed 后）"""
    _wake_event.set()
