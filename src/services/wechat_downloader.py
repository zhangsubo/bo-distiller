"""
微信文章下载器

通过 down.mptext.top 公共 API 下载微信文章全文，
支持图片本地化与正文回写数据库。

限速说明：令牌桶在本模块 download() 内统一执行（按 wechat.requests_per_minute），
队列 worker 与单篇下载端点共用同一限速器，避免打爆 API。
"""

import hashlib
import re
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup
from rich.console import Console

from src.config import get_config_manager
from src.models import Article

console = Console()

# 常见浏览器 UA（微信图片允许空 Referer，带 UA 即可）
_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# 需要本地化的微信图片域名
_WECHAT_IMG_DOMAINS = ("mmbiz.qpic.cn", "mmbiz.qlogo.cn")

# Content-Type -> 扩展名
_CONTENT_TYPE_EXT = {
    "image/jpeg": ".jpeg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/bmp": ".bmp",
}

# 令牌桶状态（模块级，进程内所有调用方共享）
_rate_lock = threading.Lock()
_last_api_call = 0.0


def _rate_limit():
    """令牌桶限速：相邻两次 API 调用至少间隔 60/rpm 秒"""
    global _last_api_call
    rpm = get_config_manager().load_config().wechat.requests_per_minute
    interval = 60.0 / max(rpm, 1)
    with _rate_lock:
        wait = interval - (time.monotonic() - _last_api_call)
        if wait > 0:
            time.sleep(wait)
        _last_api_call = time.monotonic()


class WeChatDownloader:
    """微信文章下载器"""

    def __init__(self, config_manager=None):
        self.config_manager = config_manager or get_config_manager()
        self.wechat_config = self.config_manager.load_config().wechat

    # ==================== 下载 ====================

    def download(self, url: str, format: str) -> str:
        """调用公共 API 下载单篇文章

        Args:
            url: 微信文章 URL
            format: markdown 或 html

        Returns:
            文章文本内容

        Raises:
            RuntimeError: 重试后仍失败
        """
        api = f"{self.wechat_config.api_base}/api/public/v1/download"
        headers = {"User-Agent": _BROWSER_UA}
        if self.wechat_config.api_token:
            headers["X-Api-Token"] = self.wechat_config.api_token

        last_error: Optional[Exception] = None
        # 首次 + 重试 2 次（退避 2s / 5s）
        for attempt, backoff in enumerate([0, 2, 5]):
            if backoff:
                time.sleep(backoff)
            try:
                _rate_limit()
                resp = requests.get(
                    api,
                    params={"url": url, "format": format},
                    headers=headers,
                    timeout=30,
                )
                resp.raise_for_status()
                # 响应无 charset 时 requests 默认按 ISO-8859-1 解码，中文会乱码
                resp.encoding = resp.apparent_encoding or "utf-8"
                text = resp.text

                # 校验内容完整性（过短通常是验证码/失败页）
                if format == "html":
                    if "js_content" not in text or len(text) <= 500:
                        raise ValueError("HTML 响应不完整（可能触发验证码）")
                else:
                    if len(text) <= 200:
                        raise ValueError("Markdown 响应过短（可能触发验证码）")
                return text
            except Exception as e:
                last_error = e
                console.print(f"[yellow]下载失败（第 {attempt + 1} 次）: {e}[/yellow]")

        raise RuntimeError(f"下载失败: {last_error}")

    # ==================== 图片本地化 ====================

    @staticmethod
    def _is_wechat_image(url: str) -> bool:
        """判断是否为微信图片 URL"""
        return any(domain in url for domain in _WECHAT_IMG_DOMAINS)

    def localize_images(self, content: str, fmt: str, article_dir: Path) -> str:
        """将微信图片 URL 替换为本地相对路径

        单图失败保留原 URL 继续；同一 URL 只下载一次。

        Args:
            content: 文章文本（markdown 或 html）
            fmt: markdown 或 html
            article_dir: 文章目录（图片存到其 images/ 子目录）

        Returns:
            替换后的内容
        """
        images_dir = article_dir / "images"

        # 收集候选图片 URL（保序去重）
        urls: List[str] = []
        if fmt == "html":
            soup = BeautifulSoup(content, "lxml")
            for img in soup.find_all("img"):
                for attr in ("src", "data-src"):
                    u = img.get(attr)
                    if u and self._is_wechat_image(u):
                        urls.append(u)
            # 内联样式 url(...)
            for u in re.findall(r"url\((https?://[^)]+)\)", content):
                u = u.strip("'\"")
                if self._is_wechat_image(u):
                    urls.append(u)
        else:
            for u in re.findall(r"!\[[^\]]*\]\((https?://[^)]+)\)", content):
                if self._is_wechat_image(u):
                    urls.append(u)

        # 逐个下载并建立映射
        mapping: Dict[str, str] = {}
        for u in dict.fromkeys(urls):
            local = self._download_image(u, images_dir)
            if local:
                mapping[u] = local
            time.sleep(0.5)

        # 替换（HTML 中 & 可能被转义为 &amp;，两种形式都替换）
        for u, local in mapping.items():
            content = content.replace(u, local)
            if "&" in u:
                content = content.replace(u.replace("&", "&amp;"), local)
        return content

    def _download_image(self, url: str, images_dir: Path) -> Optional[str]:
        """下载单张图片，成功返回相对路径 images/{filename}，失败返回 None"""
        name_base = hashlib.md5(url.encode()).hexdigest()[:16]
        try:
            # 已下载过（任意扩展名）则直接复用，保证同一 URL 只下载一次
            if images_dir.exists():
                existing = list(images_dir.glob(f"{name_base}.*"))
                if existing:
                    return f"images/{existing[0].name}"

            resp = requests.get(
                url, headers={"User-Agent": _BROWSER_UA}, timeout=15
            )
            resp.raise_for_status()
            ext = self._guess_ext(url, resp.headers.get("Content-Type", ""))
            filename = f"{name_base}{ext}"
            images_dir.mkdir(parents=True, exist_ok=True)
            (images_dir / filename).write_bytes(resp.content)
            return f"images/{filename}"
        except Exception as e:
            console.print(f"[yellow]图片下载失败，保留原 URL: {url[:80]} ({e})[/yellow]")
            return None

    @staticmethod
    def _guess_ext(url: str, content_type: str) -> str:
        """从 Content-Type 或 URL 推断图片扩展名，默认 .jpeg"""
        ct = content_type.split(";")[0].strip().lower()
        if ct in _CONTENT_TYPE_EXT:
            return _CONTENT_TYPE_EXT[ct]
        # 微信图片常带 wx_fmt= 参数
        m = re.search(r"wx_fmt=(\w+)", url)
        if m:
            fmt = m.group(1).lower()
            return ".jpg" if fmt == "jpg" else f".{fmt}"
        return ".jpeg"

    # ==================== 文章处理 ====================

    @staticmethod
    def _safe_title(title: str) -> str:
        """清洗标题为安全目录名（去除非法字符和控制字符，截断 60 字）"""
        cleaned = re.sub(r'[/\\:*?"<>|\x00-\x1f]', "_", title).strip()
        return cleaned[:60] or "untitled"

    def process_article(self, article: Article) -> Dict[str, str]:
        """下载并保存单篇文章（按配置格式），可选回写正文

        Args:
            article: 文章对象

        Returns:
            {格式: 文件路径} 字典
        """
        cfg = self.wechat_config

        # 目录：{storage_dir}/{YYYY-MM}/{safe_title}_{article_id[:8]}/
        date = article.published_date or article.fetched_date
        month_dir = date.strftime("%Y-%m") if date else "unknown"
        safe_title = self._safe_title(article.title)
        article_dir = Path(cfg.storage_dir) / month_dir / f"{safe_title}_{article.id[:8]}"
        article_dir.mkdir(parents=True, exist_ok=True)

        files: Dict[str, str] = {}
        markdown_content: Optional[str] = None
        html_content: Optional[str] = None

        for fmt in cfg.formats:
            content = self.download(article.url, fmt)
            if cfg.localize_images:
                content = self.localize_images(content, fmt, article_dir)
            if fmt == "markdown":
                file_path = article_dir / "article.md"
                file_path.write_text(content, encoding="utf-8")
                files["markdown"] = str(file_path)
                markdown_content = content
            elif fmt == "html":
                file_path = article_dir / "article.html"
                file_path.write_text(content, encoding="utf-8")
                files["html"] = str(file_path)
                html_content = content

        # 回写正文到数据库（先取出最新记录再改，保持其他字段不变）
        if cfg.write_back_content:
            new_content = markdown_content
            if not new_content and html_content:
                new_content = BeautifulSoup(html_content, "lxml").get_text("\n")
            if new_content:
                from src.storage import get_storage

                storage = get_storage()
                stored = storage.get_article(article.id)
                if stored:
                    stored.content = new_content
                    stored.metadata["wechat_files"] = files
                    stored.metadata["wechat_downloaded_at"] = datetime.now().isoformat()
                    storage.save_article(stored)

        return files
