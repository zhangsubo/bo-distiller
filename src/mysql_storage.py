"""
MySQL 存储管理模块

提供基于 MySQL 的文章持久化存储，支持增量更新和查询。
"""

import json
from datetime import datetime
from typing import Dict, List, Optional

import pymysql
from dbutils.pooled_db import PooledDB
from rich.console import Console

from .models import Article, SourceInfo, SourceType
from .storage_base import StorageBase

console = Console()


class MySQLStorage(StorageBase):
    """MySQL 存储管理器"""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 3306,
        user: str = "root",
        password: str = "",
        database: str = "distill",
        charset: str = "utf8mb4",
    ):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.charset = charset

        # 创建连接池
        self.pool = PooledDB(
            creator=pymysql,
            maxconnections=10,
            mincached=2,
            maxcached=5,
            blocking=True,
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database,
            charset=self.charset,
            cursorclass=pymysql.cursors.DictCursor,
        )

        self._init_db()

    def _get_conn(self):
        """从连接池获取连接"""
        return self.pool.connection()

    @staticmethod
    def _decode_json(value, default=None):
        """统一解码 MySQL JSON 字段

        PyMySQL 对 JSON 列通常返回 str，偶尔返回已解析的 dict/list。
        此 helper 保证对外始终返回 Python 对象。
        """
        if value is None:
            return default if default is not None else {}
        if isinstance(value, (dict, list)):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, ValueError):
                return default if default is not None else {}
        return default if default is not None else {}

    def _init_db(self):
        """初始化数据库表结构"""
        conn = self._get_conn()
        try:
            with conn.cursor() as cursor:
                # 文章表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS articles (
                        id VARCHAR(255) PRIMARY KEY,
                        title TEXT NOT NULL,
                        content LONGTEXT,
                        url TEXT,
                        source_type VARCHAR(50) NOT NULL,
                        source_name VARCHAR(255) NOT NULL,
                        source_identifier VARCHAR(255),
                        author VARCHAR(255),
                        published_date DATETIME,
                        fetched_date DATETIME NOT NULL,
                        metadata JSON,
                        url_duplicate TINYINT DEFAULT 0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        INDEX idx_source (source_type, source_name),
                        INDEX idx_fetched (fetched_date),
                        INDEX idx_url (url(255))
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)

                # 同步状态表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS sync_state (
                        source_type VARCHAR(50) NOT NULL,
                        source_name VARCHAR(255) NOT NULL,
                        last_sync DATETIME,
                        total_articles INT DEFAULT 0,
                        metadata JSON,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        PRIMARY KEY (source_type, source_name)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)

                # 主题表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS topics (
                        name VARCHAR(255) PRIMARY KEY,
                        keywords JSON,
                        article_count INT DEFAULT 0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)

                # 知识文档表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS knowledge_docs (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        topic VARCHAR(255) NOT NULL,
                        content LONGTEXT NOT NULL,
                        article_count INT DEFAULT 0,
                        batch_count INT DEFAULT 0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        metadata JSON,
                        INDEX idx_topic (topic)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)

                # 设置表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS settings (
                        `key` VARCHAR(255) PRIMARY KEY,
                        value JSON NOT NULL,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)

            conn.commit()
        finally:
            conn.close()

    # ==================== 文章操作 ====================

    def _upsert_article(self, cursor, article: Article) -> None:
        """在已有连接中插入或更新单篇文章"""
        cursor.execute("""
            INSERT INTO articles (id, title, content, url, source_type, source_name,
                source_identifier, author, published_date, fetched_date, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                title = VALUES(title),
                content = VALUES(content),
                url = VALUES(url),
                author = VALUES(author),
                published_date = VALUES(published_date),
                metadata = VALUES(metadata),
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
            article.published_date if article.published_date else None,
            article.fetched_date if article.fetched_date else datetime.now(),
            json.dumps(article.metadata, ensure_ascii=False)
        ))

    def save_article(self, article: Article) -> None:
        """保存单篇文章"""
        conn = self._get_conn()
        try:
            with conn.cursor() as cursor:
                self._upsert_article(cursor, article)
            conn.commit()
        finally:
            conn.close()

    def save_articles(self, articles: List[Article]) -> int:
        """批量保存文章，返回保存数量"""
        saved = 0
        conn = self._get_conn()
        try:
            with conn.cursor() as cursor:
                for article in articles:
                    try:
                        self._upsert_article(cursor, article)
                        saved += 1
                    except Exception as e:
                        console.print(f"[yellow]保存文章失败 [{article.id}]: {e}[/yellow]")
            conn.commit()
        finally:
            conn.close()
        return saved

    def get_article(self, article_id: str) -> Optional[Article]:
        """获取单篇文章"""
        conn = self._get_conn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM articles WHERE id = %s", (article_id,))
                row = cursor.fetchone()
                if row:
                    return self._row_to_article(row)
        finally:
            conn.close()
        return None

    def get_all_articles(self, limit: Optional[int] = None, offset: int = 0) -> List[Article]:
        """获取所有文章"""
        conn = self._get_conn()
        try:
            with conn.cursor() as cursor:
                query = "SELECT * FROM articles ORDER BY fetched_date DESC"
                if limit:
                    query += f" LIMIT {limit} OFFSET {offset}"
                cursor.execute(query)
                rows = cursor.fetchall()
                return [self._row_to_article(row) for row in rows]
        finally:
            conn.close()

    def get_articles_by_source(self, source_type: str, source_name: str = None) -> List[Article]:
        """按来源获取文章"""
        conn = self._get_conn()
        try:
            with conn.cursor() as cursor:
                if source_name:
                    cursor.execute(
                        "SELECT * FROM articles WHERE source_type = %s AND source_name = %s ORDER BY fetched_date DESC",
                        (source_type, source_name)
                    )
                else:
                    cursor.execute(
                        "SELECT * FROM articles WHERE source_type = %s ORDER BY fetched_date DESC",
                        (source_type,)
                    )
                rows = cursor.fetchall()
                return [self._row_to_article(row) for row in rows]
        finally:
            conn.close()

    def get_article_count(self) -> int:
        """获取文章总数"""
        conn = self._get_conn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) as count FROM articles")
                return cursor.fetchone()['count']
        finally:
            conn.close()

    def search_articles(self, keyword: str) -> List[Article]:
        """搜索文章"""
        conn = self._get_conn()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM articles WHERE title LIKE %s OR content LIKE %s ORDER BY fetched_date DESC",
                    (f"%{keyword}%", f"%{keyword}%")
                )
                rows = cursor.fetchall()
                return [self._row_to_article(row) for row in rows]
        finally:
            conn.close()

    def delete_article(self, article_id: str) -> bool:
        """删除文章"""
        conn = self._get_conn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM articles WHERE id = %s", (article_id,))
                conn.commit()
                return cursor.rowcount > 0
        finally:
            conn.close()

    def _row_to_article(self, row: Dict) -> Article:
        """将数据库行转换为 Article 对象"""
        source_type = row['source_type']
        try:
            st = SourceType(source_type)
        except ValueError:
            st = SourceType.LOCAL_FILE

        metadata = self._decode_json(row['metadata'], {})

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
            published_date=row['published_date'],
            fetched_date=row['fetched_date'] if row['fetched_date'] else datetime.now(),
            metadata=metadata
        )

    # ==================== URL 重复标记 ====================

    def mark_url_duplicates(self) -> int:
        """标记 URL 重复的文章（同一 URL 只保留最早的一条为 0）"""
        conn = self._get_conn()
        try:
            with conn.cursor() as cursor:
                # 先标记所有为非重复
                cursor.execute("UPDATE articles SET url_duplicate = 0")

                # 找出重复 URL（保留每组中 id 最小的一条）
                cursor.execute("""
                    UPDATE articles a1
                    INNER JOIN (
                        SELECT url, MIN(id) as min_id
                        FROM articles
                        WHERE url IS NOT NULL AND url != ''
                        GROUP BY url
                        HAVING COUNT(*) > 1
                    ) a2 ON a1.url = a2.url
                    SET a1.url_duplicate = 1
                    WHERE a1.id != a2.min_id
                """)

                changes = cursor.rowcount
            conn.commit()
            return changes
        finally:
            conn.close()

    def filter_url_duplicates(self, articles: List[Article]) -> List[Article]:
        """过滤掉数据库中标记为 URL 重复的文章"""
        if not articles:
            return articles

        ids_to_check = [a.id for a in articles]
        placeholders = ",".join(["%s"] * len(ids_to_check))

        conn = self._get_conn()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"SELECT id FROM articles WHERE id IN ({placeholders}) AND url_duplicate = 1",
                    ids_to_check
                )
                rows = cursor.fetchall()
        finally:
            conn.close()

        duplicate_ids = {row["id"] for row in rows}
        return [a for a in articles if a.id not in duplicate_ids]

    # ==================== 同步状态操作 ====================

    def get_sync_state(self, source_type: str, source_name: str) -> Optional[Dict]:
        """获取同步状态"""
        conn = self._get_conn()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM sync_state WHERE source_type = %s AND source_name = %s",
                    (source_type, source_name)
                )
                row = cursor.fetchone()
                if row:
                    return {
                        'last_sync': row['last_sync'].isoformat() if row['last_sync'] else None,
                        'total_articles': row['total_articles'],
                        'metadata': self._decode_json(row['metadata'], {})
                    }
        finally:
            conn.close()
        return None

    def update_sync_state(
        self,
        source_type: str,
        source_name: str,
        last_sync: str = None,
        total_articles: int = None,
        metadata: Dict = None,
    ) -> None:
        """更新同步状态"""
        conn = self._get_conn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO sync_state (source_type, source_name, last_sync, total_articles, metadata)
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        last_sync = COALESCE(VALUES(last_sync), last_sync),
                        total_articles = COALESCE(VALUES(total_articles), total_articles),
                        metadata = COALESCE(VALUES(metadata), metadata),
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    source_type,
                    source_name,
                    last_sync,
                    total_articles,
                    json.dumps(metadata, ensure_ascii=False) if metadata else None
                ))
            conn.commit()
        finally:
            conn.close()

    # ==================== 主题操作 ====================

    def get_topics(self) -> Dict[str, List[str]]:
        """获取所有主题"""
        conn = self._get_conn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT name, keywords FROM topics")
                rows = cursor.fetchall()
                return {row['name']: self._decode_json(row['keywords'], []) for row in rows}
        finally:
            conn.close()

    def set_topic(self, name: str, keywords: List[str], article_count: int = 0) -> None:
        """设置主题"""
        conn = self._get_conn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO topics (name, keywords, article_count)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        keywords = VALUES(keywords),
                        article_count = VALUES(article_count),
                        updated_at = CURRENT_TIMESTAMP
                """, (name, json.dumps(keywords, ensure_ascii=False), article_count))
            conn.commit()
        finally:
            conn.close()

    # ==================== 知识文档操作 ====================

    def save_knowledge_doc(
        self,
        topic: str,
        content: str,
        article_count: int = 0,
        batch_count: int = 0,
        metadata: Dict = None,
    ) -> int:
        """保存知识文档，返回文档 ID"""
        conn = self._get_conn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO knowledge_docs (topic, content, article_count, batch_count, metadata)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    topic,
                    content,
                    article_count,
                    batch_count,
                    json.dumps(metadata, ensure_ascii=False) if metadata else None
                ))
                conn.commit()
                return cursor.lastrowid
        finally:
            conn.close()

    def get_knowledge_docs(self, topic: str = None) -> List[Dict]:
        """获取知识文档"""
        conn = self._get_conn()
        try:
            with conn.cursor() as cursor:
                if topic:
                    cursor.execute(
                        "SELECT * FROM knowledge_docs WHERE topic = %s ORDER BY created_at DESC",
                        (topic,)
                    )
                else:
                    cursor.execute("SELECT * FROM knowledge_docs ORDER BY created_at DESC")
                rows = cursor.fetchall()
                for row in rows:
                    if row.get('created_at'):
                        row['created_at'] = row['created_at'].isoformat()
                    row['metadata'] = self._decode_json(row.get('metadata'), {})
                return rows
        finally:
            conn.close()

    # ==================== 设置操作 ====================

    def get_setting(self, key: str) -> Optional[Dict]:
        """获取设置"""
        conn = self._get_conn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT value FROM settings WHERE `key` = %s", (key,))
                row = cursor.fetchone()
                if row:
                    return self._decode_json(row['value'])
        finally:
            conn.close()
        return None

    def set_setting(self, key: str, value: Dict) -> None:
        """设置配置"""
        conn = self._get_conn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO settings (`key`, value)
                    VALUES (%s, %s)
                    ON DUPLICATE KEY UPDATE
                        value = VALUES(value),
                        updated_at = CURRENT_TIMESTAMP
                """, (key, json.dumps(value, ensure_ascii=False)))
            conn.commit()
        finally:
            conn.close()

    def delete_setting(self, key: str) -> bool:
        """删除设置"""
        conn = self._get_conn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM settings WHERE `key` = %s", (key,))
                conn.commit()
                return cursor.rowcount > 0
        finally:
            conn.close()

    def get_all_settings(self) -> Dict[str, Dict]:
        """获取所有设置"""
        conn = self._get_conn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT `key`, value FROM settings")
                rows = cursor.fetchall()
                return {row['key']: self._decode_json(row['value'], {}) for row in rows}
        finally:
            conn.close()

    # ==================== 统计 ====================

    def get_stats(self) -> Dict:
        """获取存储统计信息"""
        conn = self._get_conn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) as count FROM articles")
                article_count = cursor.fetchone()['count']

                cursor.execute("""
                    SELECT source_type, source_name, COUNT(*) as count
                    FROM articles
                    GROUP BY source_type, source_name
                """)
                source_stats = cursor.fetchall()

                return {
                    'total_articles': article_count,
                    'sources': source_stats,
                    'db_type': 'mysql',
                    'db_host': f"{self.host}:{self.port}",
                    'db_name': self.database
                }
        finally:
            conn.close()
