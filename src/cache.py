"""
Bo-Distiller 缓存管理模块

实现断点续传功能，支持多层缓存。
所有派生缓存使用确定性指纹，确保输入或配置变化时自动失效。
"""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console

from .models import Article, CacheProgress
from .storage import SQLiteStorage, get_storage

console = Console()

# 缓存 schema 版本：变更时所有旧缓存自动失效
CACHE_SCHEMA_VERSION = 2


class CacheManager:
    """缓存管理器 - 支持断点续传

    缓存层级：
    1. 原始内容（articles.pkl 或 SQLite）
    2. 清洗结果（cleaned.json）- 指纹 = 有序文章 ID + 正文 hash
    3. 主题分类（topics.json）- 指纹 = cleaned 指纹 + 主题配置
    4. 批次结果（batches/）- 指纹 = topic + 批次文章 + prompt + model + temperature
    5. 最终文档（final/）- 指纹 = 有序 batch 结果 + 整合 prompt + model + temperature
    """

    def __init__(self, cache_dir: str = ".cache", use_sqlite: bool = True):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.use_sqlite = use_sqlite

        # SQLite 存储
        self._storage: Optional[SQLiteStorage] = None
        if use_sqlite:
            self._storage = get_storage()

        # 缓存文件路径
        self.articles_cache = self.cache_dir / "articles.json"
        self.cleaned_cache = self.cache_dir / "cleaned.json"
        self.topics_cache = self.cache_dir / "topics.json"
        self.batches_dir = self.cache_dir / "batches"
        self.batches_dir.mkdir(parents=True, exist_ok=True)
        self.final_dir = self.cache_dir / "final"
        self.final_dir.mkdir(parents=True, exist_ok=True)

        # 指纹 manifest（用于诊断缓存命中原因）
        self.manifest_file = self.cache_dir / "manifest.json"

        # 进度文件
        self.progress_file = self.cache_dir / "progress.json"

    @staticmethod
    def _stable_hash(data: Any) -> str:
        """生成确定性 SHA-256 指纹（前 16 位 hex）

        使用 sort_keys 保证 dict 序列化顺序一致。
        """
        if isinstance(data, str):
            payload = data.encode("utf-8")
        else:
            payload = json.dumps(data, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()[:16]

    def get_cache_key(self, data: Any) -> str:
        """生成缓存键（基于数据的确定性 hash）"""
        return self._stable_hash(data)

    def _save_manifest(self, layer: str, fingerprint: str, meta: Dict) -> None:
        """保存缓存 manifest 便于诊断命中原因"""
        manifest = {}
        if self.manifest_file.exists():
            try:
                manifest = json.loads(self.manifest_file.read_text(encoding="utf-8"))
            except Exception:
                manifest = {}
        manifest[layer] = {
            "fingerprint": fingerprint,
            "schema_version": CACHE_SCHEMA_VERSION,
            **meta,
        }
        self.manifest_file.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    def _read_manifest(self, layer: str) -> Optional[Dict]:
        """读取指定层的 manifest"""
        if not self.manifest_file.exists():
            return None
        try:
            manifest = json.loads(self.manifest_file.read_text(encoding="utf-8"))
            return manifest.get(layer)
        except Exception:
            return None

    def _safe_filename(self, raw_name: str) -> str:
        """将任意字符串转为安全的文件名（hash）"""
        return self._stable_hash(raw_name)

    # ==================== 原始内容缓存 ====================

    def save_articles(self, articles: List[Article]) -> None:
        if self.use_sqlite and self._storage:
            saved = self._storage.save_articles(articles)
            console.print(f"[dim]>> SQLite：保存 {saved} 篇原始文章[/dim]")
        else:
            data = [a.model_dump(mode="json") for a in articles]
            self.articles_cache.write_text(
                json.dumps(data, ensure_ascii=False, default=str), encoding="utf-8"
            )
            console.print(f"[dim]>> 缓存：保存 {len(articles)} 篇原始文章[/dim]")

    def load_articles(self) -> Optional[List[Article]]:
        if self.use_sqlite and self._storage:
            articles = self._storage.get_all_articles()
            if articles:
                console.print(f"[yellow]>> SQLite：读取 {len(articles)} 篇原始文章[/yellow]")
                return articles
            return None

        if self.articles_cache.exists():
            data = json.loads(self.articles_cache.read_text(encoding="utf-8"))
            articles = [Article(**item) for item in data]
            console.print(f"[yellow]>> 缓存：读取 {len(articles)} 篇原始文章[/yellow]")
            return articles
        return None

    # ==================== 清洗结果缓存 ====================

    def _cleaned_fingerprint(self, articles: List[Article]) -> str:
        """清洗结果指纹：有序文章 ID + 正文 hash + schema 版本"""
        parts = [
            {"id": a.id, "content_hash": self._stable_hash(a.content)}
            for a in articles
        ]
        return self._stable_hash({
            "version": CACHE_SCHEMA_VERSION,
            "articles": parts,
        })

    def save_cleaned(self, cleaned: List[Article]) -> None:
        data = [a.model_dump(mode="json") for a in cleaned]
        self.cleaned_cache.write_text(
            json.dumps(data, ensure_ascii=False, default=str), encoding="utf-8"
        )
        console.print(f"[dim]>> 缓存：保存 {len(cleaned)} 篇清洗后文章[/dim]")

    def load_cleaned(self, articles: Optional[List[Article]] = None) -> Optional[List[Article]]:
        """加载清洗结果（带指纹校验）

        Args:
            articles: 原始文章列表，用于校验指纹。None 时跳过校验。
        """
        if not self.cleaned_cache.exists():
            return None

        # 如果提供了 articles，校验指纹
        if articles is not None:
            expected_fp = self._cleaned_fingerprint(articles)
            manifest = self._read_manifest("cleaned")
            if manifest and manifest.get("fingerprint") != expected_fp:
                console.print("[yellow]>> 清洗缓存指纹不匹配，跳过[/yellow]")
                return None

        data = json.loads(self.cleaned_cache.read_text(encoding="utf-8"))
        cleaned = [Article(**item) for item in data]
        console.print(f"[yellow]>> 缓存：读取 {len(cleaned)} 篇清洗后文章[/yellow]")
        return cleaned

    def save_cleaned_with_fingerprint(self, cleaned: List[Article], articles: List[Article]) -> None:
        """保存清洗结果并记录指纹"""
        fp = self._cleaned_fingerprint(articles)
        self.save_cleaned(cleaned)
        self._save_manifest("cleaned", fp, {"article_count": len(cleaned)})

    # ==================== 主题分类缓存 ====================

    def _topics_fingerprint(self, cleaned: List[Article], topics_config: Any) -> str:
        """主题分类指纹：cleaned 指纹 + 主题配置"""
        cleaned_fp = self._cleaned_fingerprint(cleaned)
        config_str = str(topics_config) if topics_config else ""
        return self._stable_hash({
            "version": CACHE_SCHEMA_VERSION,
            "cleaned_fp": cleaned_fp,
            "topics_config": config_str,
        })

    def save_topics(self, topics: Dict[str, List[Article]]) -> None:
        data = {k: [a.model_dump(mode="json") for a in v] for k, v in topics.items()}
        self.topics_cache.write_text(
            json.dumps(data, ensure_ascii=False, default=str), encoding="utf-8"
        )
        total = sum(len(v) for v in topics.values())
        console.print(f"[dim]>> 缓存：保存主题分类结果（{total}篇）[/dim]")

    def load_topics(
        self,
        cleaned: Optional[List[Article]] = None,
        topics_config: Any = None,
    ) -> Optional[Dict[str, List[Article]]]:
        """加载主题分类结果（带指纹校验）

        Args:
            cleaned: 清洗后的文章列表，用于校验指纹。None 时跳过校验。
            topics_config: 主题配置，用于校验指纹。
        """
        if not self.topics_cache.exists():
            return None

        if cleaned is not None:
            expected_fp = self._topics_fingerprint(cleaned, topics_config)
            manifest = self._read_manifest("topics")
            if manifest and manifest.get("fingerprint") != expected_fp:
                console.print("[yellow]>> 主题分类缓存指纹不匹配，跳过[/yellow]")
                return None

        data = json.loads(self.topics_cache.read_text(encoding="utf-8"))
        topics = {k: [Article(**item) for item in v] for k, v in data.items()}
        total = sum(len(v) for v in topics.values())
        console.print(f"[yellow]>> 缓存：读取主题分类结果（{total}篇）[/yellow]")
        return topics

    def save_topics_with_fingerprint(
        self,
        topics: Dict[str, List[Article]],
        cleaned: List[Article],
        topics_config: Any,
    ) -> None:
        """保存主题分类结果并记录指纹"""
        fp = self._topics_fingerprint(cleaned, topics_config)
        self.save_topics(topics)
        self._save_manifest("topics", fp, {"topic_count": len(topics)})

    # ==================== 批次结果缓存 ====================

    def _batch_fingerprint(
        self,
        topic: str,
        batch_idx: int,
        articles: List[Article],
        prompt_key: str,
        provider_id: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """批次指纹：topic + 批次文章 + 提取参数"""
        article_parts = [
            {"id": a.id, "content_hash": self._stable_hash(a.content)}
            for a in articles
        ]
        return self._stable_hash({
            "version": CACHE_SCHEMA_VERSION,
            "topic": topic,
            "batch_idx": batch_idx,
            "articles": article_parts,
            "prompt_key": prompt_key,
            "provider_id": provider_id,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
        })

    def save_batch_result(
        self,
        topic: str,
        batch_idx: int,
        result: str,
        fingerprint: Optional[str] = None,
    ) -> None:
        """保存单个批次的合成结果"""
        safe_name = self._safe_filename(f"{topic}_batch_{batch_idx}")
        if fingerprint:
            safe_name = f"{fingerprint[:12]}_{safe_name}"
        cache_file = self.batches_dir / f"{safe_name}.txt"
        with open(cache_file, "w", encoding="utf-8") as f:
            f.write(result)
        console.print(f"[dim]>> 缓存：保存【{topic}】批次 {batch_idx}[/dim]")

    def load_batch_result(
        self,
        topic: str,
        batch_idx: int,
        fingerprint: Optional[str] = None,
    ) -> Optional[str]:
        """加载单个批次的合成结果"""
        safe_name = self._safe_filename(f"{topic}_batch_{batch_idx}")
        if fingerprint:
            safe_name = f"{fingerprint[:12]}_{safe_name}"
        cache_file = self.batches_dir / f"{safe_name}.txt"
        if cache_file.exists():
            with open(cache_file, "r", encoding="utf-8") as f:
                return f.read()
        return None

    def get_completed_batches(
        self,
        topic: str,
        total_batches: int,
        fingerprint: Optional[str] = None,
    ) -> List[int]:
        """获取已完成的批次列表"""
        completed = []
        for i in range(total_batches):
            safe_name = self._safe_filename(f"{topic}_batch_{i}")
            if fingerprint:
                safe_name = f"{fingerprint[:12]}_{safe_name}"
            if (self.batches_dir / f"{safe_name}.txt").exists():
                completed.append(i)
        return completed

    # ==================== 最终文档缓存 ====================

    def _final_fingerprint(
        self,
        topic: str,
        batch_results: List[str],
        prompt_key: str,
        provider_id: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """最终文档指纹：有序 batch 结果 hash + 整合参数"""
        batch_hashes = [self._stable_hash(r) for r in batch_results]
        return self._stable_hash({
            "version": CACHE_SCHEMA_VERSION,
            "topic": topic,
            "batch_hashes": batch_hashes,
            "prompt_key": prompt_key,
            "provider_id": provider_id,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
        })

    def save_final_doc(
        self,
        topic: str,
        content: str,
        fingerprint: Optional[str] = None,
    ) -> None:
        """保存最终合成结果"""
        safe_name = self._safe_filename(topic)
        if fingerprint:
            safe_name = f"{fingerprint[:12]}_{safe_name}"
        cache_file = self.final_dir / f"{safe_name}_final.txt"
        with open(cache_file, "w", encoding="utf-8") as f:
            f.write(content)
        console.print(f"[dim]>> 缓存：保存【{topic}】最终合成[/dim]")

    def load_final_doc(
        self,
        topic: str,
        fingerprint: Optional[str] = None,
    ) -> Optional[str]:
        """加载最终合成结果"""
        safe_name = self._safe_filename(topic)
        if fingerprint:
            safe_name = f"{fingerprint[:12]}_{safe_name}"
        cache_file = self.final_dir / f"{safe_name}_final.txt"
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
            "schema_version": CACHE_SCHEMA_VERSION,
        }
