"""
微信文章下载 API

回填入队、状态查询、单篇下载、失败重试、配置读写
"""

from pathlib import Path

import yaml
from fastapi import APIRouter, HTTPException

from src.config import get_config_manager
from src.services.wechat_queue import (
    WECHAT_URL_KEYWORD,
    get_current,
    scan_and_enqueue_pending,
    wake_worker,
)
from src.web.deps import _get_storage

router = APIRouter()


# ==================== 微信文章下载 API ====================

@router.post("/api/wechat/backfill")
async def backfill_wechat():
    """扫描库中微信文章并登记入队（幂等）"""
    try:
        enqueued = scan_and_enqueue_pending()
        stats = _get_storage().get_download_stats()
        return {"enqueued": enqueued, "stats": stats}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/wechat/status")
async def get_wechat_status():
    """获取下载队列状态"""
    try:
        enabled = get_config_manager().load_config().wechat.enabled
        return {
            "stats": _get_storage().get_download_stats(),
            "current": get_current(),
            "enabled": enabled,
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/wechat/download/{article_id}")
async def download_wechat_article(article_id: str):
    """同步下载单篇微信文章（走统一限速器）"""
    from src.services.wechat_downloader import WeChatDownloader

    storage = _get_storage()
    article = storage.get_article(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    if not article.url or WECHAT_URL_KEYWORD not in article.url:
        raise HTTPException(status_code=400, detail="不是微信文章 URL")

    # 已完成则直接返回
    existing = storage.get_download(article_id)
    if existing and existing["status"] == "done" and existing["files"]:
        return {"status": "ok", "files": existing["files"], "already_done": True}

    # 登记并同步执行下载
    storage.enqueue_downloads([{"article_id": article_id, "url": article.url}])
    storage.update_download_status(article_id, "downloading")
    try:
        downloader = WeChatDownloader()
        files = downloader.process_article(article)
        storage.update_download_status(article_id, "done", files=files)
        return {"status": "ok", "files": files}
    except Exception as e:
        import traceback
        traceback.print_exc()
        storage.update_download_status(article_id, "failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/wechat/retry-failed")
async def retry_failed_downloads():
    """将失败任务重置为 pending 并唤醒 worker"""
    try:
        reset = _get_storage().reset_failed_to_pending()
        if reset:
            wake_worker()
        return {"reset": reset}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/wechat/config")
async def get_wechat_config():
    """获取 config.yaml 的 wechat 段"""
    config_file = Path("config.yaml")
    if not config_file.exists():
        return {"config": {}}
    try:
        with open(config_file, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return {"config": data.get("wechat", {})}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/wechat/config")
async def save_wechat_config(config: dict):
    """保存 config.yaml 的 wechat 段（下次处理时生效，不热重载队列）"""
    config_file = Path("config.yaml")
    try:
        with open(config_file, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        data["wechat"] = config
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
