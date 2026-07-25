"""
微信本地化下载 API

提供扫码登录、公众号搜索、文章同步、下载管理等功能的 Web 接口。
"""

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.services.wechat_native import WechatAuth, WechatAPI, NativeWechatDownloader
from src.web.deps import _get_storage
import yaml

router = APIRouter(prefix="/api/wechat-native", tags=["wechat-native"])


# ==================== 请求/响应模型 ====================

class LoginStatusResponse(BaseModel):
    """登录状态响应"""
    authenticated: bool
    message: str
    cookie_file: Optional[str] = None


class SearchAccountRequest(BaseModel):
    """搜索公众号请求"""
    keyword: str


class AccountInfo(BaseModel):
    """公众号信息"""
    fakeid: str
    nickname: str
    alias: str
    signature: str


class SyncArticlesRequest(BaseModel):
    """同步文章列表请求"""
    fakeid: str
    nickname: str
    max_articles: Optional[int] = None


class DownloadRequest(BaseModel):
    """下载请求"""
    limit: Optional[int] = None


class StatsResponse(BaseModel):
    """统计信息响应"""
    total: int
    pending: int
    downloading: int
    done: int
    failed: int


# ==================== 辅助函数 ====================

def _load_config() -> dict:
    """加载配置"""
    config_path = Path(__file__).parent.parent.parent / "services/wechat_native/config.yaml"
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _get_auth() -> WechatAuth:
    """获取认证实例"""
    config = _load_config()
    return WechatAuth(
        cookie_file=config["auth"]["cookie_file"],
        token_expire_days=config["auth"]["token_expire_days"],
    )


def _get_api() -> WechatAPI:
    """获取 API 实例"""
    auth = _get_auth()
    if not auth.load_cookie():
        raise HTTPException(status_code=401, detail="未登录，请先扫码登录")
    if not auth.is_authenticated():
        raise HTTPException(status_code=401, detail="认证已失效，请重新登录")

    config = _load_config()
    return WechatAPI(auth, timeout=config["api"]["timeout"])


def _get_downloader() -> NativeWechatDownloader:
    """获取下载器实例"""
    api = _get_api()
    config = _load_config()

    return NativeWechatDownloader(
        api=api,
        db_path=config["database"]["path"],
        output_dir=config["download"]["output_dir"],
        rpm=config["download"]["rpm"],
        formats=config["download"]["formats"],
        localize_images=config["download"]["localize_images"],
        min_content_len=config["download"]["min_content_len"],
    )


# ==================== API 端点 ====================

@router.get("/status", response_model=LoginStatusResponse)
async def get_login_status():
    """
    获取登录状态

    检查当前是否已登录以及认证是否有效。
    """
    try:
        auth = _get_auth()

        if not auth.load_cookie():
            return LoginStatusResponse(
                authenticated=False,
                message="未登录",
            )

        if not auth.is_authenticated():
            return LoginStatusResponse(
                authenticated=False,
                message="认证已失效，请重新登录",
                cookie_file=str(auth.cookie_file),
            )

        return LoginStatusResponse(
            authenticated=True,
            message="已登录",
            cookie_file=str(auth.cookie_file),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/login")
async def request_login():
    """
    请求登录二维码

    注意：Web 版本暂不支持扫码登录，请使用 CLI 命令：
    ./venv/bin/python cli/wechat_native.py login
    """
    raise HTTPException(
        status_code=501,
        detail="Web 版本暂不支持扫码登录，请使用 CLI 命令：./venv/bin/python cli/wechat_native.py login"
    )


@router.post("/search")
async def search_accounts(request: SearchAccountRequest):
    """
    搜索公众号

    根据关键词搜索公众号，返回匹配的公众号列表。
    """
    try:
        api = _get_api()
        accounts = api.search_account(request.keyword)

        return {
            "accounts": [
                AccountInfo(
                    fakeid=acc.fakeid,
                    nickname=acc.nickname,
                    alias=acc.alias,
                    signature=acc.signature,
                )
                for acc in accounts
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync")
async def sync_articles(request: SyncArticlesRequest):
    """
    同步公众号文章列表

    获取指定公众号的所有文章并保存到数据库。
    """
    try:
        downloader = _get_downloader()

        # 创建临时公众号对象
        from src.services.wechat_native.api import Account
        account = Account(
            fakeid=request.fakeid,
            nickname=request.nickname,
            alias="",
        )

        # 同步文章列表
        count = downloader.sync_account(
            account_name=request.nickname,
            max_articles=request.max_articles,
        )

        return {
            "synced": count,
            "message": f"成功同步 {count} 篇文章",
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/download")
async def start_download(request: DownloadRequest):
    """
    开始下载文章

    下载数据库中待处理的文章。
    """
    try:
        downloader = _get_downloader()

        # 这里需要异步执行，避免阻塞 API
        # 暂时返回成功，实际下载在后台进行
        import threading

        def _download_task():
            try:
                downloader.download_pending(limit=request.limit)
            except Exception as e:
                print(f"下载任务出错: {e}")

        thread = threading.Thread(target=_download_task, daemon=True)
        thread.start()

        return {
            "status": "started",
            "message": f"下载任务已启动（限制: {request.limit or '无'}）",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=StatsResponse)
async def get_download_stats():
    """
    获取下载统计

    返回待下载、已完成、失败等各状态的文章数量。
    """
    try:
        downloader = _get_downloader()
        stats = downloader.get_stats()

        return StatsResponse(**stats)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/retry-failed")
async def retry_failed():
    """
    重试失败的下载

    将失败状态的文章重置为待下载。
    """
    try:
        import sqlite3
        config = _load_config()
        db_path = config["database"]["path"]

        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute(
            "UPDATE wechat_downloads SET status='pending' WHERE status='failed'"
        )
        reset_count = cursor.rowcount
        conn.commit()
        conn.close()

        return {
            "reset": reset_count,
            "message": f"已重置 {reset_count} 篇失败文章",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config")
async def get_config():
    """
    获取配置

    返回当前的配置信息。
    """
    try:
        config = _load_config()
        return {"config": config}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/config")
async def update_config(new_config: dict):
    """
    更新配置

    保存新的配置到文件。
    """
    try:
        config_path = Path(__file__).parent.parent.parent / "services/wechat_native/config.yaml"

        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(new_config, f, allow_unicode=True, default_flow_style=False)

        return {
            "status": "ok",
            "message": "配置已保存",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
