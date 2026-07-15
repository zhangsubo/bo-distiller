"""
SQLite 存储管理模块

提供文章的持久化存储，支持增量更新和查询。
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from rich.console import Console

from .models import Article, SourceInfo, SourceType

console = Console()

# 默认数据库路径
DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "distiller.db"


class SQLiteStorage:
    """SQLite 存储管理器"""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_db(self):
        """初始化数据库表结构"""
        with self._get_conn() as conn:
            conn.executescript("""
                -- 文章表
                CREATE TABLE IF NOT EXISTS articles (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT,
                    url TEXT,
                    source_type TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    source_identifier TEXT,
                    author TEXT,
                    published_date TEXT,
                    fetched_date TEXT NOT NULL,
                    metadata TEXT,  -- JSON
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                -- 索引
                CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source_type, source_name);
                CREATE INDEX IF NOT EXISTS idx_articles_fetched ON articles(fetched_date);
                CREATE INDEX IF NOT EXISTS idx_articles_url ON articles(url);

                -- 同步状态表
                CREATE TABLE IF NOT EXISTS sync_state (
                    source_type TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    last_sync TEXT,
                    total_articles INTEGER DEFAULT 0,
                    metadata TEXT,  -- JSON
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (source_type, source_name)
                );

                -- 主题表
                CREATE TABLE IF NOT EXISTS topics (
                    name TEXT PRIMARY KEY,
                    keywords TEXT,  -- JSON array
                    article_count INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                -- 知识文档表
                CREATE TABLE IF NOT EXISTS knowledge_docs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT NOT NULL,
                    content TEXT NOT NULL,
                    article_count INTEGER DEFAULT 0,
                    batch_count INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT  -- JSON
                );

                CREATE INDEX IF NOT EXISTS idx_docs_topic ON knowledge_docs(topic);
            """)

    # ==================== 文章操作 ====================

    def save_article(self, article: Article) -> None:
        """保存单篇文章"""
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO articles (id, title, content, url, source_type, source_name,
                    source_identifier, author, published_date, fetched_date, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title = excluded.title,
                    content = excluded.content,
                    url = excluded.url,
                    author = excluded.author,
                    published_date = excluded.published_date,
                    metadata = excluded.metadata,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                article.id,
                article.title,
                article.content,
                article.url,
                article.source.type.value if isinstance(article.source.type, SourceType) else article.source.type,
                article.source.name,
                article.source.identifier,
                article.author,
                article.published_date.isoformat() if article.published_date else None,
                article.fetched_date.isoformat() if article.fetched_date else datetime.now().isoformat(),
                json.dumps(article.metadata, ensure_ascii=False)
            ))

    def save_articles(self, articles: List[Article]) -> int:
        """批量保存文章，返回保存数量"""
        saved = 0
        with self._get_conn() as conn:
            for article in articles:
                try:
                    conn.execute("""
                        INSERT INTO articles (id, title, content, url, source_type, source_name,
                            source_identifier, author, published_date, fetched_date, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(id) DO UPDATE SET
                            title = excluded.title,
                            content = excluded.content,
                            url = excluded.url,
                            author = excluded.author,
                            published_date = excluded.published_date,
                            metadata = excluded.metadata,
                            updated_at = CURRENT_TIMESTAMP
                    """, (
                        article.id,
                        article.title,
                        article.content,
                        article.url,
                        article.source.type.value if isinstance(article.source.type, SourceType) else article.source.type,
                        article.source.name,
                        article.source.identifier,
                        article.author,
                        article.published_date.isoformat() if article.published_date else None,
                        article.fetched_date.isoformat() if article.fetched_date else datetime.now().isoformat(),
                        json.dumps(article.metadata, ensure_ascii=False)
                    ))
                    saved += 1
                except Exception as e:
                    console.print(f"[yellow]保存文章失败 [{article.id}]: {e}[/yellow]")
        return saved

    def get_article(self, article_id: str) -> Optional[Article]:
        """获取单篇文章"""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM articles WHERE id = ?", (article_id,)
            ).fetchone()
            if row:
                return self._row_to_article(row)
        return None

    def get_all_articles(self, limit: Optional[int] = None, offset: int = 0) -> List[Article]:
        """获取所有文章"""
        with self._get_conn() as conn:
            query = "SELECT * FROM articles ORDER BY fetched_date DESC"
            if limit:
                query += f" LIMIT {limit} OFFSET {offset}"
            rows = conn.execute(query).fetchall()
            return [self._row_to_article(row) for row in rows]

    def get_articles_by_source(self, source_type: str, source_name: str = None) -> List[Article]:
        """按来源获取文章"""
        with self._get_conn() as conn:
            if source_name:
                rows = conn.execute(
                    "SELECT * FROM articles WHERE source_type = ? AND source_name = ? ORDER BY fetched_date DESC",
                    (source_type, source_name)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM articles WHERE source_type = ? ORDER BY fetched_date DESC",
                    (source_type,)
                ).fetchall()
            return [self._row_to_article(row) for row in rows]

    def get_article_count(self) -> int:
        """获取文章总数"""
        with self._get_conn() as conn:
            return conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]

    def search_articles(self, keyword: str) -> List[Article]:
        """搜索文章"""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM articles WHERE title LIKE ? OR content LIKE ? ORDER BY fetched_date DESC",
                (f"%{keyword}%", f"%{keyword}%")
            ).fetchall()
            return [self._row_to_article(row) for row in rows]

    def delete_article(self, article_id: str) -> bool:
        """删除文章"""
        with self._get_conn() as conn:
            cursor = conn.execute("DELETE FROM articles WHERE id = ?", (article_id,))
            return cursor.rowcount > 0

    def _row_to_article(self, row) -> Article:
        """将数据库行转换为 Article 对象"""
        source_type = row['source_type']
        try:
            st = SourceType(source_type)
        except ValueError:
            st = SourceType.LOCAL_FILE

        return Article(
            id=row['id'],
            title=row['title'],
            content=row['content'] or '',
            url=row['url'],
            source=SourceInfo(
                type=st,
                name=row['source_name'],
                identifier=row['source_identifier'] or ''
            ),
            author=row['author'],
            published_date=datetime.fromisoformat(row['published_date']) if row['published_date'] else None,
            fetched_date=datetime.fromisoformat(row['fetched_date']) if row['fetched_date'] else datetime.now(),
            metadata=json.loads(row['metadata']) if row['metadata'] else {}
        )

    # ==================== 同步状态操作 ====================

    def get_sync_state(self, source_type: str, source_name: str) -> Optional[Dict]:
        """获取同步状态"""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM sync_state WHERE source_type = ? AND source_name = ?",
                (source_type, source_name)
            ).fetchone()
            if row:
                return {
                    'last_sync': row['last_sync'],
                    'total_articles': row['total_articles'],
                    'metadata': json.loads(row['metadata']) if row['metadata'] else {}
                }
        return None

    def update_sync_state(self, source_type: str, source_name: str,
                          last_sync: str = None, total_articles: int = None,
                          metadata: Dict = None) -> None:
        """更新同步状态"""
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO sync_state (source_type, source_name, last_sync, total_articles, metadata, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(source_type, source_name) DO UPDATE SET
                    last_sync = COALESCE(excluded.last_sync, last_sync),
                    total_articles = COALESCE(excluded.total_articles, total_articles),
                    metadata = COALESCE(excluded.metadata, metadata),
                    updated_at = CURRENT_TIMESTAMP
            """, (
                source_type,
                source_name,
                last_sync,
                total_articles,
                json.dumps(metadata, ensure_ascii=False) if metadata else None
            ))

    # ==================== 主题操作 ====================

    def get_topics(self) -> Dict[str, List[str]]:
        """获取所有主题"""
        with self._get_conn() as conn:
            rows = conn.execute("SELECT name, keywords FROM topics").fetchall()
            return {row['name']: json.loads(row['keywords']) for row in rows}

    def set_topic(self, name: str, keywords: List[str], article_count: int = 0) -> None:
        """设置主题"""
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO topics (name, keywords, article_count, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(name) DO UPDATE SET
                    keywords = excluded.keywords,
                    article_count = excluded.article_count,
                    updated_at = CURRENT_TIMESTAMP
            """, (name, json.dumps(keywords, ensure_ascii=False), article_count))

    # ==================== 知识文档操作 ====================

    def save_knowledge_doc(self, topic: str, content: str,
                           article_count: int = 0, batch_count: int = 0,
                           metadata: Dict = None) -> int:
        """保存知识文档，返回文档 ID"""
        with self._get_conn() as conn:
            cursor = conn.execute("""
                INSERT INTO knowledge_docs (topic, content, article_count, batch_count, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (
                topic,
                content,
                article_count,
                batch_count,
                json.dumps(metadata, ensure_ascii=False) if metadata else None
            ))
            return cursor.lastrowid

    def get_knowledge_docs(self, topic: str = None) -> List[Dict]:
        """获取知识文档"""
        with self._get_conn() as conn:
            if topic:
                rows = conn.execute(
                    "SELECT * FROM knowledge_docs WHERE topic = ? ORDER BY created_at DESC",
                    (topic,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM knowledge_docs ORDER BY created_at DESC"
                ).fetchall()
            return [dict(row) for row in rows]

    # ==================== 统计 ====================

    def get_stats(self) -> Dict:
        """获取存储统计信息"""
        with self._get_conn() as conn:
            article_count = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
            source_stats = conn.execute("""
                SELECT source_type, source_name, COUNT(*) as count
                FROM articles
                GROUP BY source_type, source_name
            """).fetchall()

            return {
                'total_articles': article_count,
                'sources': [dict(row) for row in source_stats],
                'db_path': str(self.db_path),
                'db_size': self.db_path.stat().st_size if self.db_path.exists() else 0
            }


# 全局单例
_storage: Optional[SQLiteStorage] = None


def get_storage(db_path: Optional[Path] = None) -> SQLiteStorage:
    """获取存储管理器单例"""
    global _storage
    if _storage is None:
        _storage = SQLiteStorage(db_path)
    return _storage
