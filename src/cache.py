"""
Bo-Distiller 缓存管理模块

实现断点续传功能，支持多层缓存。
"""

import hashlib
import json
import pickle
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console

from .models import Article, CacheProgress
from .storage import SQLiteStorage, get_storage

console = Console()


class CacheManager:
    """缓存管理器 - 支持断点续传

    缓存层级：
    1. 原始内容（articles.pkl 或 SQLite）
    2. 清洗结果（cleaned.pkl）
    3. 主题分类（topics.pkl）
    4. 批次结果（batches/）
    5. 最终文档（final/）
    """

    def __init__(self, cache_dir: str = ".cache", use_sqlite: bool = True):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.use_sqlite = use_sqlite

        # SQLite 存储
        self._storage: Optional[SQLiteStorage] = None
        if use_sqlite:
            self._storage = get_storage()

        # 缓存文件路径（pickle 备用）
        self.articles_cache = self.cache_dir / "articles.pkl"
        self.cleaned_cache = self.cache_dir / "cleaned.pkl"
        self.topics_cache = self.cache_dir / "topics.pkl"
        self.batches_dir = self.cache_dir / "batches"
        self.batches_dir.mkdir(parents=True, exist_ok=True)
        self.final_dir = self.cache_dir / "final"
        self.final_dir.mkdir(parents=True, exist_ok=True)

        # 进度文件
        self.progress_file = self.cache_dir / "progress.json"

    def get_cache_key(self, data: Any) -> str:
        """生成缓存键（基于数据的 hash）"""
        data_str = str(data)
        return hashlib.md5(data_str.encode()).hexdigest()[:16]

    # ==================== 原始内容缓存 ====================

    def save_articles(self, articles: List[Article]) -> None:
        """保存原始文章"""
        if self.use_sqlite and self._storage:
            saved = self._storage.save_articles(articles)
            console.print(f"[dim]>> SQLite：保存 {saved} 篇原始文章[/dim]")
        else:
            with open(self.articles_cache, "wb") as f:
                pickle.dump(articles, f)
            console.print(f"[dim]>> 缓存：保存 {len(articles)} 篇原始文章[/dim]")

    def load_articles(self) -> Optional[List[Article]]:
        """加载原始文章"""
        if self.use_sqlite and self._storage:
            articles = self._storage.get_all_articles()
            if articles:
                console.print(f"[yellow]>> SQLite：读取 {len(articles)} 篇原始文章[/yellow]")
                return articles
            return None

        if self.articles_cache.exists():
            with open(self.articles_cache, "rb") as f:
                articles = pickle.load(f)
            console.print(f"[yellow]>> 缓存：读取 {len(articles)} 篇原始文章[/yellow]")
            return articles
        return None

    # ==================== 清洗结果缓存 ====================

    def save_cleaned(self, cleaned: List[Article]) -> None:
        """保存清洗后的文章"""
        with open(self.cleaned_cache, "wb") as f:
            pickle.dump(cleaned, f)
        console.print(f"[dim]>> 缓存：保存 {len(cleaned)} 篇清洗后文章[/dim]")

    def load_cleaned(self) -> Optional[List[Article]]:
        """加载清洗后的文章"""
        if self.cleaned_cache.exists():
            with open(self.cleaned_cache, "rb") as f:
                cleaned = pickle.load(f)
            console.print(f"[yellow]>> 缓存：读取 {len(cleaned)} 篇清洗后文章[/yellow]")
            return cleaned
        return None

    # ==================== 主题分类缓存 ====================

    def save_topics(self, topics: Dict[str, List[Article]]) -> None:
        """保存主题分类结果"""
        with open(self.topics_cache, "wb") as f:
            pickle.dump(topics, f)
        total = sum(len(v) for v in topics.values())
        console.print(f"[dim]>> 缓存：保存主题分类结果（{total}篇）[/dim]")

    def load_topics(self) -> Optional[Dict[str, List[Article]]]:
        """加载主题分类结果"""
        if self.topics_cache.exists():
            with open(self.topics_cache, "rb") as f:
                topics = pickle.load(f)
            total = sum(len(v) for v in topics.values())
            console.print(f"[yellow]>> 缓存：读取主题分类结果（{total}篇）[/yellow]")
            return topics
        return None

    # ==================== 批次结果缓存 ====================

    def save_batch_result(self, topic: str, batch_idx: int, result: str) -> None:
        """保存单个批次的合成结果"""
        cache_file = self.batches_dir / f"{topic}_batch_{batch_idx}.txt"
        with open(cache_file, "w", encoding="utf-8") as f:
            f.write(result)
        console.print(f"[dim]>> 缓存：保存【{topic}】批次 {batch_idx}[/dim]")

    def load_batch_result(self, topic: str, batch_idx: int) -> Optional[str]:
        """加载单个批次的合成结果"""
        cache_file = self.batches_dir / f"{topic}_batch_{batch_idx}.txt"
        if cache_file.exists():
            with open(cache_file, "r", encoding="utf-8") as f:
                return f.read()
        return None

    def get_completed_batches(self, topic: str, total_batches: int) -> List[int]:
        """获取已完成的批次列表"""
        completed = []
        for i in range(total_batches):
            if (self.batches_dir / f"{topic}_batch_{i}.txt").exists():
                completed.append(i)
        return completed

    # ==================== 最终文档缓存 ====================

    def save_final_doc(self, topic: str, content: str) -> None:
        """保存最终合成结果"""
        cache_file = self.final_dir / f"{topic}_final.txt"
        with open(cache_file, "w", encoding="utf-8") as f:
            f.write(content)
        console.print(f"[dim]>> 缓存：保存【{topic}】最终合成[/dim]")

    def load_final_doc(self, topic: str) -> Optional[str]:
        """加载最终合成结果"""
        cache_file = self.final_dir / f"{topic}_final.txt"
        if cache_file.exists():
            with open(cache_file, "r", encoding="utf-8") as f:
                return f.read()
        return None

    # ==================== 进度管理 ====================

    def save_progress(self, progress: CacheProgress) -> None:
        """保存进度信息"""
        with open(self.progress_file, "w", encoding="utf-8") as f:
            json.dump(progress.model_dump(), f, indent=2, ensure_ascii=False, default=str)

    def load_progress(self) -> Optional[CacheProgress]:
        """加载进度信息"""
        if self.progress_file.exists():
            with open(self.progress_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return CacheProgress(**data)
        return None

    # ==================== 缓存管理 ====================

    def clear_cache(self) -> None:
        """清除所有缓存"""
        import shutil

        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.batches_dir.mkdir(parents=True, exist_ok=True)
            self.final_dir.mkdir(parents=True, exist_ok=True)
        console.print("[yellow]>> 已清除所有缓存[/yellow]")

    def get_cache_info(self) -> Dict[str, Any]:
        """获取缓存信息"""
        return {
            "articles": self.articles_cache.exists(),
            "cleaned": self.cleaned_cache.exists(),
            "topics": self.topics_cache.exists(),
            "batch_count": len(list(self.batches_dir.glob("*.txt"))),
            "final_count": len(list(self.final_dir.glob("*.txt"))),
            "progress": self.progress_file.exists(),
        }
