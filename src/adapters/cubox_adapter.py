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
from rich.progress import Progress

from ..models import Article, SourceConfig, SourceInfo, SourceType
from ..storage import SQLiteStorage, get_storage
from .base import SourceAdapter

console = Console()


class CuboxAdapter(SourceAdapter):
    """Cubox CLI 适配器"""

    def __init__(self, use_sqlite: bool = True, progress_callback=None):
        self.use_sqlite = use_sqlite
        self.progress_callback = progress_callback
        self._storage: Optional[SQLiteStorage] = None
        if use_sqlite:
            self._storage = get_storage()
        self.state_file = Path(".cache/cubox_state.json")
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

    def fetch_card_detail(self, card_id: str) -> Optional[dict]:
        """获取单篇卡片完整详情（含正文、批注、AI 洞见）"""
        try:
            result = subprocess.run(
                ["cubox-cli", "card", "detail", "--id", str(card_id), "-o", "json"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                return None
            return json.loads(result.stdout)
        except Exception:
            return None

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
        """全量抓取 Cubox 收藏（含完整正文、批注、AI 洞见）"""
        console.print("[cyan]正在从 Cubox 全量抓取（含完整正文）...[/cyan]")

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
        total = len(cubox_items)
        saved_count = 0  # 已保存数量

        if self.progress_callback:
            self.progress_callback(total, 0, f"开始抓取完整正文（共 {total} 篇）...")

        with Progress() as progress:
            task = progress.add_task("[cyan]抓取完整正文...", total=total)
            for idx, item in enumerate(cubox_items):
                detail = self.fetch_card_detail(item.get("id", ""))
                article = self._parse_cubox_item(item, source_config, detail=detail)
                if article:
                    articles.append(article)

                    # 立即写入单篇文章（边抓取边写入）
                    if self.use_sqlite and self._storage:
                        try:
                            self._storage.save_article(article)
                            saved_count += 1
                        except Exception as e:
                            console.print(f"[yellow]保存文章失败 [{article.title}]: {e}[/yellow]")

                progress.advance(task)

                # 更新进度回调
                if self.progress_callback:
                    self.progress_callback(total, idx + 1, f"抓取并保存... {idx + 1}/{total} (已保存 {saved_count} 篇)")

        # 标记 URL 重复（在所有文章写入后统一处理）
        if self.use_sqlite and self._storage and saved_count > 0:
            dupes = self._storage.mark_url_duplicates()
            console.print(f"[dim]>> 成功保存 {saved_count} 篇 Cubox 文章，标记 {dupes} 条重复 URL[/dim]")
        elif saved_count == 0:
            console.print("[yellow]未保存任何文章[/yellow]")

        # 补抓空标签文章的标签（Cubox 通常在次日自动补标签）
        if self.use_sqlite and self._storage:
            self._refresh_empty_tags(source_config)

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
        """增量抓取 Cubox（基于 since 时间，含完整正文）"""
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
        total = len(cubox_items)
        saved_count = 0  # 已保存数量

        if self.progress_callback:
            self.progress_callback(total, 0, f"开始增量抓取（共 {total} 篇）...")

        with Progress() as progress:
            task = progress.add_task("[cyan]增量抓取完整正文...", total=total)
            for idx, item in enumerate(cubox_items):
                detail = self.fetch_card_detail(item.get("id", ""))
                article = self._parse_cubox_item(item, source_config, detail=detail)
                if article:
                    articles.append(article)

                    # 立即写入单篇文章（边抓取边写入）
                    if self.use_sqlite and self._storage:
                        try:
                            self._storage.save_article(article)
                            saved_count += 1
                        except Exception as e:
                            console.print(f"[yellow]保存文章失败 [{article.title}]: {e}[/yellow]")

                progress.advance(task)

                # 更新进度回调
                if self.progress_callback:
                    self.progress_callback(total, idx + 1, f"增量抓取并保存... {idx + 1}/{total} (已保存 {saved_count} 篇)")

        # 标记 URL 重复（在所有文章写入后统一处理）
        if self.use_sqlite and self._storage and saved_count > 0:
            dupes = self._storage.mark_url_duplicates()
            console.print(f"[dim]>> 成功保存 {saved_count} 篇 Cubox 增量文章，标记 {dupes} 条重复 URL[/dim]")
        elif saved_count == 0:
            console.print("[yellow]未保存任何增量文章[/yellow]")

        # 补抓空标签
        if self.use_sqlite and self._storage:
            self._refresh_empty_tags(source_config)

        # 更新状态
        if articles:
            state = self.get_state(source_config)
            state["last_sync"] = datetime.now().isoformat()
            state["total_articles"] = state.get("total_articles", 0) + len(articles)
            self.save_state(source_config, state)

        console.print(f"[green]✓ Cubox 增量: {len(articles)} 篇[/green]")
        return articles

    def _parse_cubox_item(
        self, item: dict, config: SourceConfig, detail: Optional[dict] = None
    ) -> Optional[Article]:
        """解析 Cubox 单条收藏

        Args:
            item: card list 返回的基础数据
            config: 源配置
            detail: card detail 返回的完整数据（含正文、批注、AI 洞见）
        """
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

            # 基础 metadata
            metadata = {
                "cubox_id": item.get("id"),
                "domain": item.get("domain", ""),
                "tags": item.get("tags", []),
                "folder": folder_name,
                "starred": item.get("starred", False),
                "read": item.get("read", False),
                "article_title": item.get("article_title", ""),
                "description": item.get("description", ""),
            }

            # 默认值：无 detail 时用 list 数据
            content = item.get("description", "") or item.get("article_title", "")
            author = item.get("domain")

            if detail:
                # 有完整详情：覆盖 content 和 author
                full_content = detail.get("content", "")
                if full_content:
                    content = full_content
                author = detail.get("author") or item.get("domain")

                # 存储批注
                annotations = detail.get("annotations", [])
                if annotations:
                    metadata["annotations"] = annotations

                # 存储 AI 洞见（摘要 + Q&A）
                insight = detail.get("insight")
                if insight:
                    metadata["insight"] = {
                        "summary": insight.get("summary", ""),
                        "qas": insight.get("qas", []),
                    }
                metadata["has_full_content"] = True
            else:
                metadata["has_full_content"] = False

            return Article(
                id=article_id,
                title=item.get("title", "无标题"),
                content=content,
                url=item.get("url"),
                source=SourceInfo(
                    type=SourceType.CUBOX,
                    name=config.name,
                    identifier=config.identifier,
                ),
                author=author,
                published_date=published_date,
                fetched_date=fetched_date,
                metadata=metadata,
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

    def _refresh_empty_tags(self, source_config: SourceConfig) -> int:
        """补抓空标签文章的标签

        Cubox 通常在收藏次日才自动打标签，每次同步时检查已有文章中
        标签为空的条目，重新拉取 detail，如果标签已更新则写回数据库。
        """
        if not self.use_sqlite or not self._storage:
            return 0

        articles = self._storage.get_articles_by_source("cubox", source_config.name)
        need_refresh = []
        for a in articles:
            tags = (a.metadata or {}).get("tags", [])
            if not tags:
                need_refresh.append(a)

        if not need_refresh:
            return 0

        console.print(f"[dim]>> 检查 {len(need_refresh)} 篇空标签文章是否已更新标签...[/dim]")
        updated = 0
        total = len(need_refresh)

        if self.progress_callback:
            self.progress_callback(total, 0, f"补抓空标签文章（共 {total} 篇）...")

        for idx, article in enumerate(need_refresh):
            cubox_id = (article.metadata or {}).get("cubox_id", article.id)
            detail = self.fetch_card_detail(cubox_id)

            # 更新进度
            if self.progress_callback:
                self.progress_callback(total, idx + 1, f"补抓空标签... {idx + 1}/{total}")

            if not detail:
                continue

            new_tags = detail.get("tags", [])
            if not new_tags:
                continue

            # 标签已更新，写回
            meta = article.metadata or {}
            meta["tags"] = new_tags

            # 同时更新可能缺失的 insight 和 annotations
            if not meta.get("insight") and detail.get("insight"):
                insight = detail["insight"]
                meta["insight"] = {
                    "summary": insight.get("summary", ""),
                    "qas": insight.get("qas", []),
                }
            if not meta.get("annotations") and detail.get("annotations"):
                meta["annotations"] = detail["annotations"]

            updated_article = Article(
                id=article.id,
                title=article.title,
                content=detail.get("content") or article.content,
                url=article.url,
                source=article.source,
                author=detail.get("author") or article.author,
                published_date=article.published_date,
                fetched_date=article.fetched_date,
                metadata=meta,
            )
            self._storage.save_article(updated_article)
            updated += 1

        if updated:
            console.print(f"[green]>> 标签补全：{updated} 篇文章获得新标签[/green]")
        return updated

    def backfill_full_content(self, source_config: SourceConfig, limit: int = 0) -> int:
        """为已有文章补抓完整正文、批注和 AI 洞见

        只处理 metadata 中 has_full_content != True 的文章。

        Args:
            source_config: 源配置
            limit: 最多处理篇数（0=不限制）

        Returns:
            成功补抓的篇数
        """
        if not self.use_sqlite or not self._storage:
            console.print("[red]backfill 需要 SQLite 存储[/red]")
            return 0

        # 找出缺少完整内容的 Cubox 文章
        articles = self._storage.get_articles_by_source("cubox", source_config.name)
        need_backfill = []
        for a in articles:
            meta = a.metadata or {}
            if not meta.get("has_full_content"):
                need_backfill.append(a)

        if not need_backfill:
            console.print("[green]所有文章已有完整内容[/green]")
            return 0

        if limit > 0:
            need_backfill = need_backfill[:limit]

        console.print(f"[cyan]需要补抓 {len(need_backfill)} 篇文章的完整内容[/cyan]")
        success = 0

        with Progress() as progress:
            task = progress.add_task("[cyan]补抓完整正文...", total=len(need_backfill))
            for article in need_backfill:
                cubox_id = (article.metadata or {}).get("cubox_id", article.id)
                detail = self.fetch_card_detail(cubox_id)
                if detail:
                    # 更新 content、author、metadata
                    full_content = detail.get("content", "")
                    real_author = detail.get("author") or article.author
                    meta = article.metadata or {}
                    meta["has_full_content"] = True
                    meta["description"] = meta.get("description") or article.content[:200]

                    annotations = detail.get("annotations", [])
                    if annotations:
                        meta["annotations"] = annotations

                    insight = detail.get("insight")
                    if insight:
                        meta["insight"] = {
                            "summary": insight.get("summary", ""),
                            "qas": insight.get("qas", []),
                        }

                    updated = Article(
                        id=article.id,
                        title=article.title,
                        content=full_content or article.content,
                        url=article.url,
                        source=article.source,
                        author=real_author,
                        published_date=article.published_date,
                        fetched_date=article.fetched_date,
                        metadata=meta,
                    )
                    self._storage.save_article(updated)
                    success += 1
                progress.advance(task)

        console.print(f"[green]✓ 补抓完成：{success}/{len(need_backfill)} 篇[/green]")
        return success
