#!/usr/bin/env python3
"""
微信文章批量下载器（独立自包含版本）

从 urls.jsonl 读取任务，通过 down.mptext.top 公共 API 下载微信文章，
支持断点续传（sqlite 状态库）、固定间隔限速、图片本地化、优雅退出。

不依赖 bo-distiller 项目代码，仅依赖 pip 第三方库。
"""

import argparse
import hashlib
import json
import re
import signal
import sqlite3
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# 常见浏览器 UA（微信图片允许空 Referer，带 UA 即可）
BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# 需要本地化的微信图片域名
WECHAT_IMG_DOMAINS = ("mmbiz.qpic.cn", "mmbiz.qlogo.cn")

# Content-Type -> 扩展名
CONTENT_TYPE_EXT = {
    "image/jpeg": ".jpeg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/bmp": ".bmp",
}


def log(msg: str):
    """带时间戳的单行日志（flush 保证 nohup 下实时可见）"""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


# ==================== 限速器 ====================

class RateLimiter:
    """固定间隔限速器：相邻两次 API 调用至少间隔 60/rpm 秒"""

    def __init__(self, rpm: int):
        self.interval = 60.0 / max(rpm, 1)
        self._lock = threading.Lock()
        self._last_call = 0.0

    def wait(self):
        with self._lock:
            delay = self.interval - (time.monotonic() - self._last_call)
            if delay > 0:
                time.sleep(delay)
            self._last_call = time.monotonic()


# ==================== 状态库（断点续传） ====================

class JobStore:
    """下载任务状态库（sqlite）"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    url TEXT,
                    title TEXT,
                    published_date TEXT,
                    status TEXT DEFAULT 'pending',
                    attempts INTEGER DEFAULT 0,
                    last_error TEXT,
                    files TEXT,  -- JSON
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
            """)

    def import_urls(self, urls_file: Path) -> int:
        """把 urls.jsonl 导入状态库（INSERT OR IGNORE），返回新增数量"""
        inserted = 0
        with open(urls_file, encoding="utf-8") as f, self._connect() as conn:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                item = json.loads(line)
                cursor = conn.execute(
                    "INSERT OR IGNORE INTO jobs (id, url, title, published_date) "
                    "VALUES (?, ?, ?, ?)",
                    (item["id"], item.get("url"), item.get("title"),
                     item.get("published_date")),
                )
                inserted += cursor.rowcount
        return inserted

    def reset_downloading(self) -> int:
        """downloading 重置为 pending（崩溃恢复），返回重置数量"""
        with self._connect() as conn:
            cursor = conn.execute("""
                UPDATE jobs SET status = 'pending', updated_at = CURRENT_TIMESTAMP
                WHERE status = 'downloading'
            """)
            return cursor.rowcount

    def next_pending(self):
        """取一条 pending 任务，无则返回 None"""
        with self._connect() as conn:
            return conn.execute(
                "SELECT * FROM jobs WHERE status = 'pending' ORDER BY created_at LIMIT 1"
            ).fetchone()

    def mark_downloading(self, job_id: str):
        with self._connect() as conn:
            conn.execute(
                "UPDATE jobs SET status = 'downloading', updated_at = CURRENT_TIMESTAMP "
                "WHERE id = ?", (job_id,))

    def mark_done(self, job_id: str, files: dict):
        with self._connect() as conn:
            conn.execute(
                "UPDATE jobs SET status = 'done', files = ?, last_error = NULL, "
                "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (json.dumps(files, ensure_ascii=False), job_id))

    def mark_failed(self, job_id: str, error: str):
        with self._connect() as conn:
            conn.execute(
                "UPDATE jobs SET status = 'failed', last_error = ?, attempts = attempts + 1, "
                "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (error, job_id))

    def stats(self) -> dict:
        """各状态计数 + 总数"""
        result = {"pending": 0, "downloading": 0, "done": 0, "failed": 0, "total": 0}
        with self._connect() as conn:
            for row in conn.execute("SELECT status, COUNT(*) AS c FROM jobs GROUP BY status"):
                result[row["status"]] = row["c"]
                result["total"] += row["c"]
        return result


# ==================== 下载与图片本地化 ====================

def download_page(api_base: str, token: str, url: str, fmt: str,
                  limiter: RateLimiter) -> str:
    """调用公共 API 下载单篇文章（最多尝试 3 次，失败后间隔 3s 重试）

    Raises:
        RuntimeError: 3 次都失败
    """
    api = f"{api_base}/api/public/v1/download"
    headers = {"User-Agent": BROWSER_UA}
    if token:
        headers["X-Api-Token"] = token

    last_error = None
    for attempt, backoff in enumerate([0, 3, 3]):
        if backoff:
            time.sleep(backoff)
        try:
            limiter.wait()
            resp = requests.get(api, params={"url": url, "format": fmt},
                                headers=headers, timeout=30)
            resp.raise_for_status()
            # 响应无 charset 时 requests 默认 ISO-8859-1，中文会乱码
            resp.encoding = resp.apparent_encoding or "utf-8"
            text = resp.text

            # 校验内容完整性（过短通常是验证码/失败页）
            if fmt == "html":
                if "js_content" not in text or len(text) <= 500:
                    raise ValueError("HTML 响应不完整（可能触发验证码）")
            else:
                if len(text) <= 200:
                    raise ValueError("Markdown 响应过短（可能触发验证码）")
            return text
        except Exception as e:
            last_error = e
            log(f"  下载失败（第 {attempt + 1} 次）: {e}")
    raise RuntimeError(f"下载失败: {last_error}")


def is_wechat_image(url: str) -> bool:
    """判断是否为微信图片 URL"""
    return any(domain in url for domain in WECHAT_IMG_DOMAINS)


def guess_ext(url: str, content_type: str) -> str:
    """从 Content-Type 或 URL 推断图片扩展名，默认 .jpeg"""
    ct = content_type.split(";")[0].strip().lower()
    if ct in CONTENT_TYPE_EXT:
        return CONTENT_TYPE_EXT[ct]
    m = re.search(r"wx_fmt=(\w+)", url)  # 微信图片常带 wx_fmt= 参数
    if m:
        fmt = m.group(1).lower()
        return ".jpg" if fmt == "jpg" else f".{fmt}"
    return ".jpeg"


def download_image(url: str, images_dir: Path):
    """下载单张图片，成功返回 images/{filename}，失败返回 None（保留原 URL）"""
    name_base = hashlib.md5(url.encode()).hexdigest()[:16]
    try:
        # 已下载过（任意扩展名）直接复用，保证同一 URL 只下载一次
        if images_dir.exists():
            existing = list(images_dir.glob(f"{name_base}.*"))
            if existing:
                return f"images/{existing[0].name}"
        resp = requests.get(url, headers={"User-Agent": BROWSER_UA}, timeout=15)
        resp.raise_for_status()
        ext = guess_ext(url, resp.headers.get("Content-Type", ""))
        filename = f"{name_base}{ext}"
        images_dir.mkdir(parents=True, exist_ok=True)
        (images_dir / filename).write_bytes(resp.content)
        return f"images/{filename}"
    except Exception as e:
        log(f"  图片下载失败，保留原 URL: {url[:80]} ({e})")
        return None


def localize_images(content: str, fmt: str, article_dir: Path) -> str:
    """将微信图片 URL 替换为本地相对路径（单图失败不阻断）"""
    images_dir = article_dir / "images"

    # 收集候选图片 URL
    urls = []
    if fmt == "html":
        soup = BeautifulSoup(content, "html.parser")
        for img in soup.find_all("img"):
            for attr in ("src", "data-src"):
                u = img.get(attr)
                if u and is_wechat_image(u):
                    urls.append(u)
        for u in re.findall(r"url\((https?://[^)]+)\)", content):  # 内联样式
            u = u.strip("'\"")
            if is_wechat_image(u):
                urls.append(u)
    else:
        for u in re.findall(r"!\[[^\]]*\]\((https?://[^)]+)\)", content):
            if is_wechat_image(u):
                urls.append(u)

    # 保序去重后逐个下载
    mapping = {}
    for u in dict.fromkeys(urls):
        local = download_image(u, images_dir)
        if local:
            mapping[u] = local
        time.sleep(0.5)

    # 替换（HTML 中 & 可能被转义为 &amp;，两种形式都替换）
    for u, local in mapping.items():
        content = content.replace(u, local)
        if "&" in u:
            content = content.replace(u.replace("&", "&amp;"), local)
    return content


def safe_title(title: str) -> str:
    """清洗标题为安全目录名（去除非法字符和控制字符，截断 60 字）"""
    cleaned = re.sub(r'[/\\:*?"<>|\x00-\x1f]', "_", title or "").strip()
    return cleaned[:60] or "untitled"


def process_job(job, cfg: dict, limiter: RateLimiter) -> dict:
    """下载并保存单篇文章，返回 {格式: 文件路径}"""
    # 落盘目录：{output}/{YYYY-MM}/{safe_title}_{id[:8]}/
    month = "unknown"
    if job["published_date"]:
        try:
            month = datetime.fromisoformat(
                job["published_date"].replace("Z", "+00:00")).strftime("%Y-%m")
        except Exception:
            pass
    if month == "unknown":
        month = datetime.now().strftime("%Y-%m")

    article_dir = (Path(cfg["output"]) / month
                   / f"{safe_title(job['title'])}_{job['id'][:8]}")
    article_dir.mkdir(parents=True, exist_ok=True)

    files = {}
    for fmt in cfg["formats"].split(","):
        fmt = fmt.strip()
        if fmt not in ("markdown", "html"):
            continue
        content = download_page(cfg["api_base"], cfg["api_token"], job["url"], fmt, limiter)
        if cfg["localize_images"]:
            content = localize_images(content, fmt, article_dir)
        if fmt == "markdown":
            path = article_dir / "article.md"
        else:
            path = article_dir / "article.html"
        path.write_text(content, encoding="utf-8")
        files[fmt] = str(path)
    return files


# ==================== 主流程 ====================

# 内置默认配置（优先级：CLI 参数 > config.yaml > 内置默认）
DEFAULT_CONFIG = {
    "api_base": "https://down.mptext.top",
    "api_token": "",
    "rpm": 1,
    "formats": "markdown,html",
    "localize_images": True,
    "output": "./wechat_articles",
    "urls": "./urls.jsonl",
    "state": "./jobs.db",
}

# 信号处理需要访问的全局状态库路径
_state_db_path = None


def load_config_file(config_path: Path) -> dict:
    """读取 config.yaml，不存在或为空返回空 dict"""
    if not config_path.exists():
        return {}
    import yaml
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def resolve_config(cli_args) -> tuple:
    """按 CLI > config.yaml > 内置默认 合并配置

    Returns:
        (生效配置 dict, 各项来源 dict)
    """
    # 配置文件路径：--config 指定，否则 download.py 同目录的 config.yaml
    if cli_args.config:
        config_path = Path(cli_args.config)
    else:
        config_path = Path(__file__).parent / "config.yaml"
    file_cfg = load_config_file(config_path)

    # 配置键 -> CLI 参数属性名 的映射
    cli_map = {
        "api_base": "api_base",
        "api_token": "token",
        "rpm": "rpm",
        "formats": "formats",
        "output": "output",
        "urls": "urls",
        "state": "state",
    }

    merged, sources = {}, {}
    for key, default in DEFAULT_CONFIG.items():
        if key == "localize_images":
            # CLI 只有 --no-images 反向开关，单独处理
            if cli_args.no_images:
                merged[key], sources[key] = False, "cli"
            elif key in file_cfg:
                merged[key], sources[key] = bool(file_cfg[key]), "config"
            else:
                merged[key], sources[key] = default, "default"
            continue

        cli_val = getattr(cli_args, cli_map[key], None)
        if cli_val is not None:
            merged[key], sources[key] = cli_val, "cli"
        elif key in file_cfg:
            merged[key], sources[key] = file_cfg[key], "config"
        else:
            merged[key], sources[key] = default, "default"

    # formats 在配置文件里是列表，统一归一为逗号分隔字符串
    if isinstance(merged["formats"], list):
        merged["formats"] = ",".join(str(f) for f in merged["formats"])

    return merged, sources, config_path


def mask_token(token: str) -> str:
    """隐藏 api_token，只显示前 4 位"""
    if not token:
        return "(空)"
    return f"{token[:4]}***" if len(token) > 4 else "***"


def _handle_signal(signum, frame):
    """SIGINT/SIGTERM：把 downloading 重置为 pending 后退出"""
    log(f"收到信号 {signum}，恢复中断任务后退出...")
    if _state_db_path:
        try:
            store = JobStore(_state_db_path)
            reset = store.reset_downloading()
            if reset:
                log(f"已恢复 {reset} 条中断任务为 pending")
        except Exception:
            pass
    sys.exit(0)


def main():
    global _state_db_path

    parser = argparse.ArgumentParser(description="微信文章批量下载器（断点续传）")
    parser.add_argument("--config", help="配置文件路径（默认取 download.py 同目录 config.yaml）")
    parser.add_argument("--urls", help="urls.jsonl 任务清单")
    parser.add_argument("--output", help="落盘根目录")
    parser.add_argument("--api-base", help="下载 API 地址")
    parser.add_argument("--token", help="X-Api-Token（会员限速更高）")
    parser.add_argument("--rpm", type=int, help="每分钟 API 请求数（游客 1，会员 60）")
    parser.add_argument("--formats", help="下载格式，逗号分隔")
    parser.add_argument("--no-images", action="store_true", help="关闭图片本地化")
    parser.add_argument("--state", help="断点状态库路径")
    parser.add_argument("--status", action="store_true", help="打印进度统计后退出，不下载")
    cli_args = parser.parse_args()

    # 合并配置：CLI > config.yaml > 内置默认
    cfg, sources, config_path = resolve_config(cli_args)

    # 打印生效配置及来源（token 脱敏）
    log(f"配置文件: {config_path}{'（未找到，仅用 CLI/默认值）' if not config_path.exists() else ''}")
    for key in DEFAULT_CONFIG:
        display = mask_token(str(cfg[key])) if key == "api_token" else cfg[key]
        log(f"  {key} = {display}  (来源: {sources[key]})")

    store = JobStore(Path(cfg["state"]))
    _state_db_path = store.db_path

    # 导入任务清单（幂等）
    urls_file = Path(cfg["urls"])
    if not urls_file.exists():
        raise SystemExit(f"任务清单不存在: {urls_file}")
    imported = store.import_urls(urls_file)

    # 崩溃恢复：上次中断的 downloading 重置为 pending
    reset = store.reset_downloading()

    stats = store.stats()
    log(f"任务总数 {stats['total']}（本次新导入 {imported}，恢复中断 {reset}）| "
        f"pending {stats['pending']} / done {stats['done']} / failed {stats['failed']}")

    if cli_args.status:
        return

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    limiter = RateLimiter(int(cfg["rpm"]))
    log(f"开始下载：限速 {cfg['rpm']} 次/分钟，格式 {cfg['formats']}，"
        f"图片本地化 {'开' if cfg['localize_images'] else '关'}")

    # 主循环：逐条消费，单条失败不中断
    while True:
        job = store.next_pending()
        if not job:
            break
        store.mark_downloading(job["id"])
        try:
            files = process_job(job, cfg, limiter)
            store.mark_done(job["id"], files)
            result = "成功"
        except Exception as e:
            store.mark_failed(job["id"], str(e))
            result = f"失败: {e}"

        progress = store.stats()
        finished = progress["done"] + progress["failed"]
        log(f"[{finished}/{progress['total']}] {job['title'][:40]} -> {result}")

    final = store.stats()
    log(f"全部处理完毕：done {final['done']} / failed {final['failed']} / "
        f"total {final['total']}")
    if final["failed"]:
        log("失败任务可用 SQL 重置重试: "
            "UPDATE jobs SET status='pending' WHERE status='failed';")


if __name__ == "__main__":
    main()
