"""
Bo-Distiller 知识合成模块

实现两阶段合成：批次提取 → 知识整合
"""

import asyncio
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .cache import CacheManager
from .config import ConfigManager, get_config_manager
from .llm_client import LLMClient, get_llm_client
from .models import Article, KnowledgeDoc, PromptTemplate
from .utils import count_tokens, format_articles_for_prompt, replace_article_refs

console = Console()


class DistillationCancelled(Exception):
    """蒸馏取消信号异常（从 orchestrator 层复用）"""
    pass


class KnowledgeSynthesizer:
    """知识合成器 - 核心模块

    实现两阶段合成：
    1. 批次提取：从每批文章中提取核心观点
    2. 知识整合：将所有批次结果整合成体系化文档
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        cache_manager: Optional[CacheManager] = None,
        config_manager: Optional[ConfigManager] = None,
        cancel_event: Optional[threading.Event] = None,
    ):
        self.llm = llm_client or get_llm_client()
        self.cache = cache_manager or CacheManager()
        self.config_manager = config_manager or get_config_manager()
        self._cancel_event = cancel_event

        self.config = self.config_manager.load_config()
        self.prompts = self.config_manager.load_prompts()

        try:
            self.topic_prompt_keys = {
                t.name: t.prompt_key for t in self.config_manager.load_topics()
            }
        except Exception:
            self.topic_prompt_keys = {}

        self.max_context = self.config.processing.max_context
        self.max_output = self.config.processing.max_output
        self.reserved_tokens = self.config.processing.reserved_tokens
        self.safety_margin = self.config.processing.safety_margin
        self.max_article_length = self.config.processing.max_article_length

    def check_cancelled(self):
        """在关键点调用：如果已取消则抛出异常"""
        if self._cancel_event and self._cancel_event.is_set():
            raise DistillationCancelled("蒸馏任务已被用户取消")

    def count_tokens(self, text: str) -> int:
        """统计文本的 token 数量"""
        return self.llm.count_tokens(text)

    def create_batches(self, articles: List[Article]) -> List[List[Article]]:
        batches = []
        current_batch = []
        current_tokens = 0

        available_tokens = int(
            (self.max_context - self.max_output - self.reserved_tokens)
            * self.safety_margin
        )

        for article in articles:
            content = article.content
            max_len = self.max_article_length if self.max_article_length > 0 else len(content)
            article_tokens = count_tokens(content[:max_len])

            if current_tokens + article_tokens > available_tokens and current_batch:
                batches.append(current_batch)
                current_batch = []
                current_tokens = 0

            current_batch.append(article)
            current_tokens += article_tokens

        if current_batch:
            batches.append(current_batch)

        return batches

    def extract_batch_insights(
        self,
        articles: List[Article],
        topic: str,
    ) -> str:
        articles_text = format_articles_for_prompt(articles, self.max_article_length)

        # 获取提示词：先按主题的 prompt_key 查，再按主题名查，最后回退 general
        prompt_key = self.topic_prompt_keys.get(topic)
        prompt_template = self.prompts.get(prompt_key) if prompt_key else None
        prompt_template = (
            prompt_template
            or self.prompts.get(topic)
            or self.prompts.get("general")
        )
        base_system_prompt = prompt_template.system if prompt_template else "请从文章中提取核心观点。"

        # 添加引用要求
        system_prompt = base_system_prompt + """

【重要格式要求】
1. 每个观点、方法论、案例后面，必须用括号标注来源文章编号
2. 格式：观点内容（文章1）
3. 多个来源：观点内容（文章1、2）
4. 不要重复列出文章标题，只需编号即可
5. 编号对应输入文章的 [文章N] 标记
6. 对于介绍同一工具的多篇文章，必须合并到同一个工具条目下"""

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"请分析以下 {len(articles)} 篇文章，每个观点都要标注来源编号：\n{articles_text}",
            },
        ]

        # LLM 调用前检查取消
        self.check_cancelled()
        batch_temp = self.config.processing.batch_temperature
        return self.llm.chat(
            messages=messages,
            temperature=batch_temp,
            max_tokens=self.max_output,
        )

    async def extract_batch_insights_async(
        self,
        articles: List[Article],
        topic: str,
        batch_index: int,
    ) -> tuple[int, str]:
        """异步提取批次洞察

        Args:
            articles: 文章列表
            topic: 主题名称
            batch_index: 批次索引

        Returns:
            (批次索引, 洞察内容) 元组
        """
        # 在线程池中运行同步方法
        loop = asyncio.get_event_loop()
        insight = await loop.run_in_executor(
            None,
            self.extract_batch_insights,
            articles,
            topic,
        )
        return (batch_index, insight)

    def _process_batches_sequential(
        self,
        batches: List[List[Article]],
        topic: str,
        completed_batches: List[int],
    ) -> List[str]:
        """串行处理批次（原有逻辑）"""
        batch_insights = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("合成中...", total=len(batches))

            for i, batch in enumerate(batches):
                # 检查缓存（使用指纹）
                fp = self._get_batch_fingerprint(topic, i, batch)
                if i in completed_batches:
                    cached = self.cache.load_batch_result(topic, i, fingerprint=fp)
                    if cached:
                        batch_insights.append(cached)
                        progress.update(
                            task, description=f"[{i + 1}/{len(batches)}] (使用缓存)..."
                        )
                        progress.advance(task)
                        continue

                # 处理新批次
                progress.update(
                    task, description=f"处理批次 {i + 1}/{len(batches)}..."
                )

                try:
                    insight = self.extract_batch_insights(batch, topic)
                    batch_insights.append(insight)

                    # 保存批次结果（使用指纹）
                    self.cache.save_batch_result(topic, i, insight, fingerprint=fp)

                except Exception as e:
                    console.print(f"\n[red]批次 {i + 1} 处理失败: {e}[/red]")
                    console.print("[yellow]>> 进度已保存，可使用相同命令继续[/yellow]\n")
                    raise

                progress.advance(task)

        return batch_insights

    def _process_batches_concurrent(
        self,
        batches: List[List[Article]],
        topic: str,
        completed_batches: List[int],
        max_concurrent: Optional[int] = None,
    ) -> List[str]:
        """并发处理批次"""
        # 从配置读取并发数
        if max_concurrent is None:
            config = self.config_manager.load_config()
            max_concurrent = config.processing.max_concurrent

        console.print(f"[cyan]>> 并发处理模式：最多同时处理 {max_concurrent} 个批次[/cyan]\n")

        # 准备待处理的批次
        pending_batches = []
        batch_insights = [None] * len(batches)  # 预分配结果列表

        for i, batch in enumerate(batches):
            if i in completed_batches:
                fp = self._get_batch_fingerprint(topic, i, batch)
                cached = self.cache.load_batch_result(topic, i, fingerprint=fp)
                if cached:
                    batch_insights[i] = cached
                    console.print(f"[green]批次 {i + 1}/{len(batches)} (使用缓存)[/green]")
                else:
                    pending_batches.append((i, batch))
            else:
                pending_batches.append((i, batch))

        if not pending_batches:
            return [ins for ins in batch_insights if ins is not None]

        # 异步处理待处理的批次
        async def process_all():
            semaphore = asyncio.Semaphore(max_concurrent)

            async def process_with_semaphore(batch_index, batch):
                async with semaphore:
                    console.print(f"[yellow]开始处理批次 {batch_index + 1}/{len(batches)}...[/yellow]")
                    try:
                        _, insight = await self.extract_batch_insights_async(batch, topic, batch_index)

                        # 保存批次结果（使用指纹）
                        fp = self._get_batch_fingerprint(topic, batch_index, batch)
                        self.cache.save_batch_result(topic, batch_index, insight, fingerprint=fp)
                        batch_insights[batch_index] = insight

                        console.print(f"[green]✓ 完成批次 {batch_index + 1}/{len(batches)}[/green]")
                        return insight
                    except Exception as e:
                        console.print(f"[red]✗ 批次 {batch_index + 1} 处理失败: {e}[/red]")
                        raise

            # 创建所有任务
            tasks = [
                process_with_semaphore(batch_index, batch)
                for batch_index, batch in pending_batches
            ]

            # 并发执行
            await asyncio.gather(*tasks)

        # 运行异步处理
        asyncio.run(process_all())

        return [ins for ins in batch_insights if ins is not None]

    def synthesize_batches(
        self,
        batch_results: List[str],
        topic: str,
    ) -> str:
        """整合多个批次的结果

        Args:
            batch_results: 批次提取结果列表
            topic: 主题名称

        Returns:
            整合后的知识文档
        """
        # 如果只有一批，直接返回
        if len(batch_results) == 1:
            return batch_results[0]

        # 构建整合提示词
        synthesis_prompt = self.prompts.get("synthesis")
        system_prompt = (
            synthesis_prompt.system
            if synthesis_prompt
            else "你是知识整合专家，擅长将分散的观点整合成体系化文档。"
        )

        user_template = (
            synthesis_prompt.user_template
            if synthesis_prompt and synthesis_prompt.user_template
            else "我从多批文章中提取了核心观点，现在需要你整合成一份完整、系统的文档。\n\n以下是 {batch_count} 批提取结果："
        )

        final_prompt = user_template.format(batch_count=len(batch_results))
        final_prompt += "\n\n"

        for i, insight in enumerate(batch_results, 1):
            final_prompt += f"\n\n## 批次 {i} 的提取结果\n{insight}\n"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": final_prompt},
        ]

        # LLM 调用前检查取消
        self.check_cancelled()
        synthesis_temp = self.config.processing.synthesis_temperature
        return self.llm.chat(
            messages=messages,
            temperature=synthesis_temp,
            max_tokens=self.max_output,
        )

    def _get_provider_id(self) -> str:
        """获取实际使用的 provider_id（从 llm_client 推断）"""
        return getattr(self.llm, "provider", self.config.llm.default_provider)

    def _get_batch_fingerprint(self, topic: str, batch_idx: int, articles: List[Article]) -> str:
        """计算批次指纹：包含实际 prompt 内容和 provider"""
        prompt_key = self.topic_prompt_keys.get(topic, "general")
        prompt_template = self.prompts.get(prompt_key) if prompt_key else None
        prompt_template = prompt_template or self.prompts.get(topic) or self.prompts.get("general")
        prompt_content = prompt_template.system if prompt_template else ""
        provider_id = self._get_provider_id()
        provider_cfg = self.config.llm.providers.get(provider_id, {})
        return self.cache._batch_fingerprint(
            topic=topic,
            batch_idx=batch_idx,
            articles=articles,
            prompt_key=prompt_content,  # 用实际 prompt 内容，不只是 key
            provider_id=provider_id,
            model=getattr(provider_cfg, "model", ""),
            temperature=self.config.processing.batch_temperature,
            max_tokens=self.max_output,
        )

    def _get_final_fingerprint(self, topic: str, batch_results: List[str]) -> str:
        """计算最终文档指纹：包含实际 prompt 内容和 provider"""
        synthesis_prompt = self.prompts.get("synthesis")
        prompt_content = synthesis_prompt.system if synthesis_prompt else ""
        provider_id = self._get_provider_id()
        provider_cfg = self.config.llm.providers.get(provider_id, {})
        return self.cache._final_fingerprint(
            topic=topic,
            batch_results=batch_results,
            prompt_key=prompt_content,  # 用实际 prompt 内容，不只是 key
            provider_id=provider_id,
            model=getattr(provider_cfg, "model", ""),
            temperature=self.config.processing.synthesis_temperature,
            max_tokens=self.max_output,
        )

    def distill_topic(
        self,
        articles: List[Article],
        topic: str,
        incremental: bool = True,
    ) -> str:
        """蒸馏单个主题（两阶段合成）

        Args:
            articles: 该主题的所有文章
            topic: 主题名称
            incremental: 是否使用缓存（False 时跳过所有派生缓存）

        Returns:
            合成后的知识文档内容（带文章引用和链接）
        """
        if not articles:
            return ""

        # incremental=False 时跳过 final 缓存
        if incremental:
            cached_final = self.cache.load_final_doc(topic)
            if cached_final:
                console.print(f"[green]>> 使用缓存：【{topic}】已完成合成[/green]\n")
                return replace_article_refs(cached_final, articles)


        console.print(f"\n[bold cyan]正在合成【{topic}】知识体系...[/bold cyan]")
        console.print(f"[yellow]共 {len(articles)} 篇文章[/yellow]\n")

        # 智能分批
        batches = self.create_batches(articles)
        console.print(f"[blue]智能分批：分为 {len(batches)} 批处理[/blue]")
        for i, batch in enumerate(batches, 1):
            console.print(f"  - 批次 {i}: {len(batch)} 篇文章")
        console.print()

        # 检查已完成的批次（使用指纹）
        completed_batches = []
        if incremental:
            for i in range(len(batches)):
                fp = self._get_batch_fingerprint(topic, i, batches[i])
                if self.cache.load_batch_result(topic, i, fingerprint=fp):
                    completed_batches.append(i)
            if completed_batches:
                console.print(f"[yellow]>> 发现已完成的批次: {completed_batches}[/yellow]")

        # 处理每一批（支持并发）
        batch_insights = self._process_batches_concurrent(
            batches, topic, completed_batches, max_concurrent=3
        )

        # 最终整合
        console.print(f"[yellow]最终整合 {len(batch_insights)} 批结果...[/yellow]")
        final_doc = self.synthesize_batches(batch_insights, topic)

        final_doc_with_links = replace_article_refs(final_doc, articles)

        # 写入前检查取消
        self.check_cancelled()

        # 保存最终结果（使用 topic hash 作文件名，与 load_final_doc 一致）
        self.cache.save_final_doc(topic, final_doc_with_links)

        console.print(f"[green]>> 完成【{topic}】知识合成[/green]\n")
        return final_doc_with_links

    def distill_all(
        self,
        topics: Dict[str, List[Article]],
        incremental: bool = True,
    ) -> Dict[str, KnowledgeDoc]:
        """蒸馏所有主题

        Args:
            topics: 按主题组织的文章字典
            incremental: 是否使用缓存

        Returns:
            每个主题的知识文档
        """
        results = {}

        for topic, articles in topics.items():
            if not articles:
                continue

            content = self.distill_topic(articles, topic, incremental=incremental)

            results[topic] = KnowledgeDoc(
                topic=topic,
                content=content,
                article_count=len(articles),
                batch_count=len(self.create_batches(articles)),
            )

        return results
