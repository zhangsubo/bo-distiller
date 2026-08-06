"""
存储抽象基类

定义统一的存储接口，支持 SQLite 和 MySQL 两种后端。
"""

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .models import Article


class StorageBase(ABC):
    """存储管理器抽象基类"""

    @abstractmethod
    def _init_db(self):
        """初始化数据库表结构"""
        pass

    # ==================== 文章操作 ====================

    @abstractmethod
    def save_article(self, article: Article) -> None:
        """保存单篇文章"""
        pass

    @abstractmethod
    def save_articles(self, articles: List[Article]) -> int:
        """批量保存文章，返回保存数量"""
        pass

    @abstractmethod
    def get_article(self, article_id: str) -> Optional[Article]:
        """获取单篇文章"""
        pass

    @abstractmethod
    def get_all_articles(self, limit: Optional[int] = None, offset: int = 0) -> List[Article]:
        """获取所有文章"""
        pass

    @abstractmethod
    def get_articles_by_source(self, source_type: str, source_name: str = None) -> List[Article]:
        """按来源获取文章"""
        pass

    @abstractmethod
    def get_article_count(self) -> int:
        """获取文章总数"""
        pass

    @abstractmethod
    def search_articles(self, keyword: str) -> List[Article]:
        """搜索文章"""
        pass

    @abstractmethod
    def delete_article(self, article_id: str) -> bool:
        """删除文章"""
        pass

    # ==================== URL 重复标记 ====================

    @abstractmethod
    def mark_url_duplicates(self) -> int:
        """标记 URL 重复的文章"""
        pass

    @abstractmethod
    def filter_url_duplicates(self, articles: List[Article]) -> List[Article]:
        """过滤掉数据库中标记为 URL 重复的文章"""
        pass

    # ==================== 同步状态操作 ====================

    @abstractmethod
    def get_sync_state(self, source_type: str, source_name: str) -> Optional[Dict]:
        """获取同步状态"""
        pass

    @abstractmethod
    def update_sync_state(
        self,
        source_type: str,
        source_name: str,
        last_sync: str = None,
        total_articles: int = None,
        metadata: Dict = None,
    ) -> None:
        """更新同步状态"""
        pass

    # ==================== 主题操作 ====================

    @abstractmethod
    def get_topics(self) -> Dict[str, List[str]]:
        """获取所有主题"""
        pass

    @abstractmethod
    def set_topic(self, name: str, keywords: List[str], article_count: int = 0) -> None:
        """设置主题"""
        pass

    # ==================== 知识文档操作 ====================

    @abstractmethod
    def save_knowledge_doc(
        self,
        topic: str,
        content: str,
        article_count: int = 0,
        batch_count: int = 0,
        metadata: Dict = None,
    ) -> int:
        """保存知识文档，返回文档 ID"""
        pass

    @abstractmethod
    def get_knowledge_docs(self, topic: str = None) -> List[Dict]:
        """获取知识文档"""
        pass

    # ==================== 设置操作 ====================

    @abstractmethod
    def get_setting(self, key: str) -> Optional[Dict]:
        """获取设置"""
        pass

    @abstractmethod
    def set_setting(self, key: str, value: Dict) -> None:
        """设置配置"""
        pass

    @abstractmethod
    def delete_setting(self, key: str) -> bool:
        """删除设置"""
        pass

    @abstractmethod
    def get_all_settings(self) -> Dict[str, Dict]:
        """获取所有设置"""
        pass

    # ==================== 统计 ====================

    @abstractmethod
    def get_stats(self) -> Dict:
        """获取存储统计信息"""
        pass
