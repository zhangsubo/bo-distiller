"""
Cubox CLI 适配器

通过 Cubox CLI 获取收藏内容。
"""

import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from rich.console import Console

from ..models import Article, SourceConfig, SourceInfo, SourceType
from ..storage import SQLiteStorage, get_storage
from .base import SourceAdapter

console = Console()


class CuboxAdapter(SourceAdapter):
    """Cubox CLI 适配器"""

    def __init__(self, use_sqlite: bool = True):
        self.use_sqlite = use_sqlite
        self._storage: Optional[SQLiteStorage] = None
        if use_sqlite:
            self._storage = get_storage()
        self.state_file = Path(".cache/cubox_state.json")
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

    def validate(self, source_config: SourceConfig) -> bool:
        """验证 Cubox CLI 是否可用"""
        try:
            result = subprocess.run(
                ["cubox-cli", "help"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                console.print("[green]✓ Cubox CLI 可用[/green]")
                return True
            else:
                console.print("[red]Cubox CLI 不可用[/red]")
                return False
        except FileNotFoundError:
            console.print("[red]Cubox CLI 未安装，请参考 CLI_TOOLS_GUIDE.md[/red]")
            return False
        except Exception as e:
            console.print(f"[red]Cubox CLI 验证失败: {e}[/red]")
            return False

    def fetch(self, source_config: SourceConfig) -> List[Article]:
        """全量抓取 Cubox 收藏"""
        console.print("[cyan]正在从 Cubox 全量抓取...[/cyan]")

        # 调用 Cubox CLI 导出所有收藏
        try:
            result = subprocess.run(
                ["cubox-cli", "card", "list", "--all", "-o", "json"],
                capture_output=True,
                text=True,
                timeout=120,
            )
        except subprocess.TimeoutExpired:
            raise Exception("Cubox CLI 调用超时")
        except Exception as e:
            raise Exception(f"Cubox CLI 调用失败: {e}")

        if result.returncode != 0:
            raise Exception(f"Cubox CLI 导出失败: {result.stderr}")

        # 解析 JSON 输出
        try:
            cubox_items = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise Exception(f"Cubox CLI 输出解析失败: {e}")

        articles = []
        for item in cubox_items:
            article = self._parse_cubox_item(item, source_config)
            if article:
                articles.append(article)

        # 保存到 SQLite
        if self.use_sqlite and self._storage and articles:
            saved = self._storage.save_articles(articles)
            console.print(f"[dim]>> SQLite：保存 {saved} 篇 Cubox 文章[/dim]")

        # 保存状态（最新文章的时间戳）
        if articles:
            latest_time = max(a.fetched_date for a in articles)
            self.save_state(
                source_config,
                {
                    "last_sync": latest_time.isoformat(),
                    "total_articles": len(articles),
                },
            )

        console.print(f"[green]✓ Cubox: {len(articles)} 篇[/green]")
        return articles

    def fetch_incremental(
        self, source_config: SourceConfig, since: float = 0
    ) -> List[Article]:
        """增量抓取 Cubox（基于 since 时间）"""
        since_dt = datetime.fromtimestamp(since) if since else None
        if since_dt:
            console.print(
                f"[cyan]正在从 Cubox 增量抓取（since {since_dt.date()}）...[/cyan]"
            )
        else:
            return self.fetch(source_config)

        # 调用 Cubox CLI 增量导出
        try:
            # 使用 start-time 参数进行增量抓取
            start_time = since_dt.strftime("%Y-%m-%d")
            result = subprocess.run(
                [
                    "cubox-cli",
                    "card",
                    "list",
                    "--all",
                    "--start-time",
                    start_time,
                    "-o",
                    "json",
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )
        except subprocess.TimeoutExpired:
            raise Exception("Cubox CLI 增量调用超时")
        except Exception as e:
            raise Exception(f"Cubox CLI 增量调用失败: {e}")

        if result.returncode != 0:
            raise Exception(f"Cubox CLI 增量导出失败: {result.stderr}")

        # 解析 JSON 输出
        try:
            cubox_items = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise Exception(f"Cubox CLI 输出解析失败: {e}")

        articles = []
        for item in cubox_items:
            article = self._parse_cubox_item(item, source_config)
            if article:
                articles.append(article)

        # 保存到 SQLite
        if self.use_sqlite and self._storage and articles:
            saved = self._storage.save_articles(articles)
            console.print(f"[dim]>> SQLite：保存 {saved} 篇 Cubox 增量文章[/dim]")

        # 更新状态
        if articles:
            state = self.get_state(source_config)
            state["last_sync"] = datetime.now().isoformat()
            state["total_articles"] = state.get("total_articles", 0) + len(articles)
            self.save_state(source_config, state)

        console.print(f"[green]✓ Cubox 增量: {len(articles)} 篇[/green]")
        return articles

    def _parse_cubox_item(
        self, item: dict, config: SourceConfig
    ) -> Optional[Article]:
        """解析 Cubox 单条收藏"""
        try:
            # 生成唯一 ID（使用 Cubox 的 ID）
            article_id = item.get("id", "")
            if not article_id:
                item_id = item.get("url", "")
                article_id = hashlib.md5(item_id.encode()).hexdigest()[:16]

            # 解析日期
            published_date = self._parse_date(item.get("create_time"))
            fetched_date = self._parse_date(item.get("create_time")) or datetime.now()

            # 获取文件夹信息
            folder_info = item.get("folder", {})
            folder_name = folder_info.get("name", "") if isinstance(folder_info, dict) else ""

            return Article(
                id=article_id,
                title=item.get("title", "无标题"),
                content=item.get("description", "") or item.get("article_title", ""),
                url=item.get("url"),
                source=SourceInfo(
                    type=SourceType.CUBOX,
                    name=config.name,
                    identifier=config.identifier,
                ),
                author=item.get("domain"),
                published_date=published_date,
                fetched_date=fetched_date,
                metadata={
                    "cubox_id": item.get("id"),
                    "domain": item.get("domain", ""),
                    "tags": item.get("tags", []),
                    "folder": folder_name,
                    "starred": item.get("starred", False),
                    "read": item.get("read", False),
                    "article_title": item.get("article_title", ""),
                },
            )
        except Exception as e:
            console.print(f"[yellow]解析 Cubox 项失败: {e}[/yellow]")
            return None

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """解析日期字符串"""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except Exception:
            return None

    def get_state(self, config: SourceConfig) -> dict:
        """获取 Cubox 同步状态"""
        if self.use_sqlite and self._storage:
            state = self._storage.get_sync_state("cubox", config.name)
            if state:
                return state
        # 回退到文件
        if self.state_file.exists():
            with open(self.state_file, "r") as f:
                return json.load(f)
        return {}

    def save_state(self, config: SourceConfig, state: dict) -> None:
        """保存 Cubox 同步状态"""
        if self.use_sqlite and self._storage:
            self._storage.update_sync_state(
                source_type="cubox",
                source_name=config.name,
                last_sync=state.get("last_sync"),
                total_articles=state.get("total_articles", 0),
                metadata=state
            )
        # 同时保存到文件（兼容）
        with open(self.state_file, "w") as f:
            json.dump(state, f, indent=2)

    def get_metadata(self, config: SourceConfig) -> dict:
        """获取 Cubox 元数据"""
        state = self.get_state(config)
        return {
            "source": "Cubox",
            "last_sync": state.get("last_sync"),
            "total_articles": state.get("total_articles", 0),
        }
