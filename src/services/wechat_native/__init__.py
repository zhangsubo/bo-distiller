"""
微信公众号本地化下载器

通过微信公众平台后台 API 直接抓取文章，无需依赖第三方服务。
核心能力从 wechat-article/wechat-article-exporter 项目提取并用 Python 重写。
"""

from .auth import WechatAuth
from .api import WechatAPI
from .downloader import NativeWechatDownloader

__all__ = ["WechatAuth", "WechatAPI", "NativeWechatDownloader"]
