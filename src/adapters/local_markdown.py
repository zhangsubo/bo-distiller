"""
本地 Markdown 文件夹适配器

支持全量扫描和增量扫描（基于文件修改时间）。
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import frontmatter
from rich.console import Console

from ..models import Article, SourceConfig, SourceInfo, SourceType
from .base import SourceAdapter

console = Console()


class LocalMarkdownAdapter(SourceAdapter):
    """本地 Markdown 文件夹适配器（支持增量）"""

    def __init__(self):
        self.state_file_template = ".cache/local_markdown_{folder_hash}_state.json"

    def validate(self, source_config: SourceConfig) -> bool:
        """验证目录是否存在"""
        dir_path = Path(source_config.identifier)
        if not dir_path.exists():
            console.print(f"[red]目录不存在: {dir_path}[/red]")
            return False
        if not dir_path.is_dir():
            console.print(f"[red]路径不是目录: {dir_path}[/red]")
            return False
        return True

    def fetch(self, source_config: SourceConfig) -> List[Article]:
        """全量扫描 Markdown 文件"""
        dir_path = Path(source_config.identifier)
        console.print(f"[cyan]正在扫描 {dir_path}...[/cyan]")

        articles = []
        processed_files = set()

        # 递归扫描所有 .md 文件
        for md_file in sorted(dir_path.rglob("*.md")):
            # 跳过隐藏文件和缓存目录
            if any(part.startswith(".") for part in md_file.relative_to(dir_path).parts):
                continue

            try:
                article = self._read_markdown_file(md_file, source_config)
                if article:
                    articles.append(article)
                    processed_files.add(str(md_file.relative_to(dir_path)))
            except Exception as e:
                console.print(f"[yellow]跳过 {md_file.name}: {e}[/yellow]")

        # 保存状态（文件列表 + 修改时间）
        state = {
            "last_sync": datetime.now().isoformat(),
            "processed_files": self._get_files_state(dir_path, processed_files),
        }
        self.save_state(source_config, state)

        console.print(f"[green]✓ 本地 Markdown: {len(articles)} 篇[/green]")
        return articles

    def fetch_incremental(
        self, source_config: SourceConfig, since: float = 0
    ) -> List[Article]:
        """增量扫描（仅处理新增/修改的文件）"""
        dir_path = Path(source_config.identifier)
        console.print(f"[cyan]正在增量扫描 {dir_path}...[/cyan]")

        # 加载上次的状态
        old_state = self.get_state(source_config)
        old_files = old_state.get("processed_files", {})

        articles = []
        current_files = {}

        for md_file in sorted(dir_path.rglob("*.md")):
            # 跳过隐藏文件和缓存目录
            if any(part.startswith(".") for part in md_file.relative_to(dir_path).parts):
                continue

            relative_path = str(md_file.relative_to(dir_path))
            file_mtime = md_file.stat().st_mtime

            # 检查是否是新文件或已修改
            old_mtime = old_files.get(relative_path)

            if old_mtime is None or file_mtime > old_mtime:
                # 新文件或已修改
                try:
                    article = self._read_markdown_file(md_file, source_config)
                    if article:
                        articles.append(article)
                        console.print(f"[dim]  + {relative_path}[/dim]")
                except Exception as e:
                    console.print(f"[yellow]跳过 {md_file.name}: {e}[/yellow]")

            current_files[relative_path] = file_mtime

        # 更新状态
        state = {"last_sync": datetime.now().isoformat(), "processed_files": current_files}
        self.save_state(source_config, state)

        console.print(f"[green]✓ 本地 Markdown 增量: {len(articles)} 篇[/green]")
        return articles

    def _read_markdown_file(
        self, file_path: Path, config: SourceConfig
    ) -> Optional[Article]:
        """读取单个 Markdown 文件"""
        with open(file_path, "r", encoding="utf-8") as f:
            raw_content = f.read()

        # 解析 Frontmatter
        post = frontmatter.loads(raw_content)

        # 提取元数据
        title = post.metadata.get("title", file_path.stem.replace("-", " ").replace("_", " "))

        # 生成唯一 ID
        article_id = self._generate_id(str(file_path))

        # 解析日期
        published_date = None
        if "date" in post.metadata:
            date_val = post.metadata["date"]
            if isinstance(date_val, datetime):
                published_date = date_val
            elif isinstance(date_val, str):
                try:
                    published_date = datetime.fromisoformat(date_val)
                except Exception:
                    pass

        return Article(
            id=article_id,
            title=title,
            content=post.content,
            url=f"file://{file_path.absolute()}",
            source=SourceInfo(
                type=SourceType.LOCAL_FILE,
                name=config.name,
                identifier=config.identifier,
            ),
            author=post.metadata.get("author"),
            published_date=published_date,
            fetched_date=datetime.fromtimestamp(file_path.stat().st_mtime),
            metadata={
                "file_path": str(file_path),
                "relative_path": str(file_path.relative_to(config.identifier)),
                "tags": post.metadata.get("tags", []),
                "category": post.metadata.get("category"),
                "source_url": post.metadata.get("source_url"),
            },
        )

    def _generate_id(self, identifier: str) -> str:
        """生成唯一 ID"""
        return hashlib.md5(identifier.encode()).hexdigest()[:16]

    def _get_files_state(self, dir_path: Path, files: set) -> Dict[str, float]:
        """获取文件列表的状态（路径 → 修改时间）"""
        state = {}
        for file_rel in files:
            file_path = dir_path / file_rel
            if file_path.exists():
                state[file_rel] = file_path.stat().st_mtime
        return state

    def _get_state_file(self, config: SourceConfig) -> Path:
        """获取状态文件路径（基于文件夹哈希）"""
        folder_hash = hashlib.md5(config.identifier.encode()).hexdigest()[:8]
        return Path(self.state_file_template.format(folder_hash=folder_hash))

    def get_state(self, config: SourceConfig) -> dict:
        """获取同步状态"""
        state_file = self._get_state_file(config)
        if state_file.exists():
            with open(state_file, "r") as f:
                return json.load(f)
        return {}

    def save_state(self, config: SourceConfig, state: dict) -> None:
        """保存同步状态"""
        state_file = self._get_state_file(config)
        state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)

    def get_metadata(self, config: SourceConfig) -> dict:
        """获取目录元数据"""
        dir_path = Path(config.identifier)
        state = self.get_state(config)

        # 统计 Markdown 文件数量
        md_count = len(list(dir_path.rglob("*.md")))

        return {
            "directory": config.identifier,
            "last_sync": state.get("last_sync"),
            "total_files": len(state.get("processed_files", {})),
            "md_files": md_count,
        }
