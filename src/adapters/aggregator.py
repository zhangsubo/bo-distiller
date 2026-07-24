"""
内容聚合器

统一所有内容源的入口，支持全量和增量抓取。
"""

from datetime import datetime
from typing import Dict, List, Optional

from rich.console import Console
from rich.table import Table

from ..config import ConfigManager, get_config_manager
from ..models import Article, SourceConfig
from ..storage import SQLiteStorage, get_storage
from .cubox_adapter import CuboxAdapter
from .local_markdown import LocalMarkdownAdapter

console = Console()


class ContentAggregator:
    """内容聚合器 - 统一所有源的入口"""

    def __init__(self, config_manager: Optional[ConfigManager] = None, use_sqlite: bool = True):
        self.config_manager = config_manager or get_config_manager()
        self.use_sqlite = use_sqlite

        # SQLite 存储
        self._storage: Optional[SQLiteStorage] = None
        if use_sqlite:
            self._storage = get_storage()

        # 注册适配器
        self.adapters = {
            "cubox": CuboxAdapter(use_sqlite=use_sqlite),
            "local_markdown": LocalMarkdownAdapter(),
            "local_file": LocalMarkdownAdapter(),  # 别名
        }

    def fetch_all(self, incremental: bool = False) -> List[Article]:
        """聚合所有源的内容

        Args:
            incremental: True=增量抓取, False=全量抓取

        Returns:
            去重后的文章列表
        """
        sources = self.config_manager.load_sources()
        enabled_sources = [s for s in sources if s.enabled]

        mode = "增量" if incremental else "全量"
        console.print(
            f"\n[bold]开始 {mode} 聚合 {len(enabled_sources)} 个内容源...[/bold]\n"
        )

        all_articles = []

        for source in enabled_sources:
            adapter = self.adapters.get(source.type)
            if not adapter:
                console.print(f"[red]不支持的源类型: {source.type}[/red]")
                continue

            # 验证源
            if not adapter.validate(source):
                console.print(f"[red]✗ {source.name}: 验证失败[/red]")
                continue

            # 抓取内容
            try:
                if incremental:
                    # 增量抓取：从上次同步时间开始
                    state = adapter.get_state(source)
                    last_sync = state.get("last_sync")

                    if last_sync:
                        since_dt = datetime.fromisoformat(last_sync)
                        since_ts = since_dt.timestamp()
                        articles = adapter.fetch_incremental(source, since_ts)
                    else:
                        # 首次运行，执行全量
                        console.print(
                            f"[yellow]{source.name}: 首次运行，执行全量抓取[/yellow]"
                        )
                        articles = adapter.fetch(source)
                else:
                    # 全量抓取
                    articles = adapter.fetch(source)

                all_articles.extend(articles)
                console.print(f"[green]✓ {source.name}: {len(articles)} 篇[/green]")

            except Exception as e:
                console.print(f"[red]✗ {source.name}: {e}[/red]")
                import traceback

                console.print(f"[dim]{traceback.format_exc()}[/dim]")

        # 去重（基于 ID）
        unique_articles = self._deduplicate(all_articles)

        duplicates = len(all_articles) - len(unique_articles)
        if duplicates > 0:
            console.print(f"[yellow]去重：移除 {duplicates} 篇重复文章[/yellow]")

        # 过滤数据库中标记的 URL 重复文章
        if self.use_sqlite and self._storage:
            before_count = len(unique_articles)
            unique_articles = self._storage.filter_url_duplicates(unique_articles)
            url_dupes = before_count - len(unique_articles)
            if url_dupes > 0:
                console.print(f"[yellow]URL 重复：移除 {url_dupes} 篇[/yellow]")

        # 保存到 SQLite（如果不是由适配器单独保存的话）
        if self.use_sqlite and self._storage and not incremental:
            saved = self._storage.save_articles(unique_articles)
            console.print(f"[dim]>> SQLite：保存 {saved} 篇聚合文章[/dim]")

        console.print(f"\n[bold]聚合完成：{len(unique_articles)} 篇[/bold]\n")

        return unique_articles

    def _deduplicate(self, articles: List[Article]) -> List[Article]:
        """去重（基于 ID）"""
        seen_ids = set()
        unique = []

        for article in articles:
            if article.id not in seen_ids:
                seen_ids.add(article.id)
                unique.append(article)

        return unique

    def get_sources_status(self) -> Dict[str, dict]:
        """获取所有源的状态"""
        sources = self.config_manager.load_sources()

        status = {}
        for source in sources:
            adapter = self.adapters.get(source.type)
            if not adapter:
                status[source.name] = {
                    "valid": False,
                    "error": f"不支持的类型: {source.type}",
                }
                continue

            try:
                is_valid = adapter.validate(source)
                metadata = adapter.get_metadata(source) if is_valid else {}

                status[source.name] = {
                    "valid": is_valid,
                    "type": source.type,
                    "enabled": source.enabled,
                    "metadata": metadata,
                }
            except Exception as e:
                status[source.name] = {"valid": False, "error": str(e)}

        return status

    def print_sources_status(self) -> None:
        """打印所有源的状态表格"""
        status = self.get_sources_status()

        table = Table(title="内容源状态")
        table.add_column("名称", style="cyan")
        table.add_column("类型", style="blue")
        table.add_column("状态", justify="center")
        table.add_column("信息", style="dim")

        for name, info in status.items():
            status_icon = "✓" if info.get("valid") else "✗"
            status_color = "green" if info.get("valid") else "red"
            enabled = "启用" if info.get("enabled") else "禁用"

            metadata = info.get("metadata", {})
            meta_parts = []
            if "last_sync" in metadata:
                meta_parts.append(f"上次同步: {metadata['last_sync'][:19]}")
            if "total_articles" in metadata:
                meta_parts.append(f"文章数: {metadata['total_articles']}")
            if "total_files" in metadata:
                meta_parts.append(f"文件数: {metadata['total_files']}")
            if "md_files" in metadata:
                meta_parts.append(f"MD文件: {metadata['md_files']}")

            meta_str = ", ".join(meta_parts) if meta_parts else enabled

            error = info.get("error")
            if error:
                meta_str = f"[red]{error}[/red]"

            table.add_row(
                name,
                info.get("type", "未知"),
                f"[{status_color}]{status_icon}[/{status_color}]",
                meta_str,
            )

        console.print()
        console.print(table)
        console.print()
