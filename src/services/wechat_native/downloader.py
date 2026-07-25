"""
微信文章下载器

负责调度下载任务、限速控制、断点续传、数据库集成。
"""

import json
import sqlite3
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List

import html2text
from bs4 import BeautifulSoup

from .api import WechatAPI, Article, Account
from .auth import WechatAuth


class RateLimiter:
    """固定间隔限速器"""

    def __init__(self, rpm: int):
        self.interval = 60.0 / max(rpm, 1)
        self._lock = threading.Lock()
        self._last_call = 0.0

    def wait(self):
        """等待到下次允许调用的时间"""
        with self._lock:
            delay = self.interval - (time.monotonic() - self._last_call)
            if delay > 0:
                time.sleep(delay)
            self._last_call = time.monotonic()


class NativeWechatDownloader:
    """微信文章本地化下载器"""

    def __init__(
        self,
        api: WechatAPI,
        db_path: Path,
        output_dir: Path,
        rpm: int = 60,
        formats: List[str] = None,
        localize_images: bool = True,
        min_content_len: int = 200,
    ):
        self.api = api
        self.db_path = Path(db_path)
        self.output_dir = Path(output_dir)
        self.rpm = rpm
        self.formats = formats or ["markdown", "html"]
        self.localize_images = localize_images
        self.min_content_len = min_content_len

        self.limiter = RateLimiter(rpm)
        self._init_db()

    def _init_db(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(str(self.db_path))
        conn.executescript("""
            -- articles 表可能已存在，仅添加微信特有字段
            CREATE TABLE IF NOT EXISTS articles (
                id TEXT PRIMARY KEY,
                title TEXT,
                url TEXT,
                author TEXT,
                published_date TEXT,
                content TEXT,
                source TEXT,
                metadata TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            -- 微信下载任务表
            CREATE TABLE IF NOT EXISTS wechat_downloads (
                id TEXT PRIMARY KEY,
                article_id TEXT,
                status TEXT DEFAULT 'pending',
                attempts INTEGER DEFAULT 0,
                last_error TEXT,
                files TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (article_id) REFERENCES articles(id)
            );

            -- 公众号表
            CREATE TABLE IF NOT EXISTS wechat_accounts (
                fakeid TEXT PRIMARY KEY,
                nickname TEXT,
                alias TEXT,
                signature TEXT,
                synced_at TEXT
            );
        """)
        conn.commit()
        conn.close()

    def sync_account(self, account_name: str, max_articles: Optional[int] = None) -> int:
        """
        同步指定公众号的文章列表到数据库

        Args:
            account_name: 公众号名称
            max_articles: 最大同步数量（None 表示全部）

        Returns:
            同步的文章数量
        """
        print(f"正在搜索公众号: {account_name}")

        # 1. 搜索公众号
        accounts = self.api.search_account(account_name)
        if not accounts:
            print(f"未找到公众号: {account_name}")
            return 0

        # 选择第一个匹配的公众号
        account = accounts[0]
        print(f"✓ 找到公众号: {account.nickname} (fakeid: {account.fakeid})")

        # 2. 保存公众号信息
        self._save_account(account)

        # 3. 分页获取文章列表
        total_synced = 0
        begin = 0
        page_size = 10

        while True:
            self.limiter.wait()

            print(f"获取文章列表: begin={begin}, count={page_size}")
            result = self.api.get_article_list(
                fakeid=account.fakeid,
                begin=begin,
                count=page_size,
            )

            articles = result["articles"]
            if not articles:
                break

            # 写入数据库
            synced = self._save_articles(articles, account)
            total_synced += synced

            print(f"  本页新增 {synced} 篇文章")

            # 检查是否达到最大数量
            if max_articles and total_synced >= max_articles:
                print(f"已达到最大同步数量 {max_articles}")
                break

            # 检查是否还有更多文章
            if begin + len(articles) >= result["total"]:
                break

            begin += page_size
            time.sleep(1)  # 额外延迟，避免过快

        print(f"✓ 同步完成，共 {total_synced} 篇新文章")
        return total_synced

    def _save_account(self, account: Account):
        """保存公众号信息"""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute(
            """
            INSERT OR REPLACE INTO wechat_accounts
            (fakeid, nickname, alias, signature, synced_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                account.fakeid,
                account.nickname,
                account.alias,
                account.signature,
                datetime.now().isoformat(),
            ),
        )
        conn.commit()
        conn.close()

    def _save_articles(self, articles: List[Article], account: Account) -> int:
        """保存文章列表到数据库"""
        conn = sqlite3.connect(str(self.db_path))
        synced = 0

        for article in articles:
            try:
                # 构造文章 ID（使用 aid）
                article_id = article.aid

                # 检查是否已存在
                cursor = conn.execute(
                    "SELECT id FROM articles WHERE id = ?", (article_id,)
                )
                if cursor.fetchone():
                    continue

                # 插入 articles 表
                published_date = datetime.fromtimestamp(article.update_time).isoformat()

                metadata = {
                    "fakeid": account.fakeid,
                    "account_name": account.nickname,
                    "create_time": article.create_time,
                    "update_time": article.update_time,
                    "digest": article.digest,
                    "cover": article.cover,
                    "copyright_stat": article.copyright_stat,
                    "item_show_type": article.item_show_type,
                }

                conn.execute(
                    """
                    INSERT INTO articles
                    (id, title, url, author, published_date, source, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        article_id,
                        article.title,
                        article.link,
                        article.author_name,
                        published_date,
                        "wechat",
                        json.dumps(metadata, ensure_ascii=False),
                    ),
                )

                # 插入 wechat_downloads 表（pending 状态）
                conn.execute(
                    """
                    INSERT INTO wechat_downloads (id, article_id, status)
                    VALUES (?, ?, 'pending')
                    """,
                    (article_id, article_id),
                )

                synced += 1

            except Exception as e:
                print(f"保存文章失败: {article.title} - {e}")

        conn.commit()
        conn.close()

        return synced

    def download_pending(self, limit: Optional[int] = None):
        """下载数据库中 pending 状态的文章"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row

        # 获取待下载的文章
        cursor = conn.execute(
            """
            SELECT a.*, w.status, w.attempts
            FROM articles a
            JOIN wechat_downloads w ON a.id = w.article_id
            WHERE w.status = 'pending'
            ORDER BY a.published_date DESC
            LIMIT ?
            """,
            (limit or -1,),
        )

        tasks = cursor.fetchall()
        conn.close()

        if not tasks:
            print("没有待下载的文章")
            return

        print(f"开始下载 {len(tasks)} 篇文章（限速 {self.rpm} 次/分钟）")

        for idx, task in enumerate(tasks, 1):
            article_id = task["id"]
            title = task["title"]
            url = task["url"]

            print(f"[{idx}/{len(tasks)}] {title[:40]}...")

            try:
                # 标记为 downloading
                self._update_download_status(article_id, "downloading")

                # 下载文章
                self.limiter.wait()
                files = self._download_article(article_id, url, title, task)

                # 回写全文到 articles 表
                self._update_article_content(article_id, files.get("markdown", ""))

                # 标记为 done
                self._update_download_status(article_id, "done", files=files)

                print(f"  ✓ 成功")

            except Exception as e:
                print(f"  ✗ 失败: {e}")
                self._update_download_status(article_id, "failed", error=str(e))

        print("✓ 下载完成")

    def _download_article(
        self, article_id: str, url: str, title: str, task: sqlite3.Row
    ) -> Dict[str, str]:
        """下载单篇文章"""
        # 解析 metadata 获取发布日期
        metadata = json.loads(task["metadata"] or "{}")
        published_date = task["published_date"]

        # 确定保存目录
        try:
            month = datetime.fromisoformat(published_date).strftime("%Y-%m")
        except Exception:
            month = datetime.now().strftime("%Y-%m")

        # 安全的目录名
        safe_title = self._safe_filename(title)
        article_dir = self.output_dir / month / f"{safe_title}_{article_id[:8]}"
        article_dir.mkdir(parents=True, exist_ok=True)

        files = {}

        # 下载 HTML
        raw_html = self.api.download_article(url)
        normalized_html = self.api.normalize_html(raw_html)

        # 保存 HTML
        if "html" in self.formats:
            html_path = article_dir / "article.html"
            html_path.write_text(normalized_html, encoding="utf-8")
            files["html"] = str(html_path)

        # 转换为 Markdown
        if "markdown" in self.formats:
            markdown = self._html_to_markdown(normalized_html)
            md_path = article_dir / "article.md"
            md_path.write_text(markdown, encoding="utf-8")
            files["markdown"] = str(md_path)

        # TODO: 图片本地化（可选）
        # if self.localize_images:
        #     self._localize_images(article_dir, normalized_html)

        return files

    def _html_to_markdown(self, html: str) -> str:
        """HTML 转 Markdown"""
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = False
        h.body_width = 0  # 不自动换行
        h.single_line_break = True
        return h.handle(html).strip()

    def _safe_filename(self, name: str) -> str:
        """清洗文件名"""
        import re

        # 移除非法字符
        cleaned = re.sub(r'[/\\:*?"<>|\x00-\x1f]', "_", name or "").strip()
        return cleaned[:60] or "untitled"

    def _update_download_status(
        self,
        article_id: str,
        status: str,
        files: Optional[Dict] = None,
        error: Optional[str] = None,
    ):
        """更新下载状态"""
        conn = sqlite3.connect(str(self.db_path))

        if status == "done":
            conn.execute(
                """
                UPDATE wechat_downloads
                SET status = ?, files = ?, last_error = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE article_id = ?
                """,
                (status, json.dumps(files, ensure_ascii=False), article_id),
            )
        elif status == "failed":
            conn.execute(
                """
                UPDATE wechat_downloads
                SET status = ?, last_error = ?, attempts = attempts + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE article_id = ?
                """,
                (status, error, article_id),
            )
        else:
            conn.execute(
                """
                UPDATE wechat_downloads
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE article_id = ?
                """,
                (status, article_id),
            )

        conn.commit()
        conn.close()

    def _update_article_content(self, article_id: str, content: str):
        """回写全文到 articles 表"""
        if len(content) < self.min_content_len:
            print(f"  警告: 内容过短（{len(content)} 字符），跳过回写")
            return

        conn = sqlite3.connect(str(self.db_path))
        conn.execute(
            "UPDATE articles SET content = ? WHERE id = ?",
            (content, article_id),
        )
        conn.commit()
        conn.close()

    def get_stats(self) -> Dict:
        """获取下载统计"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row

        cursor = conn.execute("""
            SELECT status, COUNT(*) as count
            FROM wechat_downloads
            GROUP BY status
        """)

        stats = {"pending": 0, "downloading": 0, "done": 0, "failed": 0, "total": 0}
        for row in cursor:
            stats[row["status"]] = row["count"]
            stats["total"] += row["count"]

        conn.close()
        return stats
