"""
Bo-Distiller 知识合成模块

实现两阶段合成：批次提取 → 知识整合
"""

import time
from pathlib import Path
from typing import Dict, List, Optional

import tiktoken
import yaml
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .cache import CacheManager
from .config import ConfigManager, get_config_manager
from .llm_client import LLMClient, get_llm_client
from .models import Article, KnowledgeDoc, PromptTemplate

console = Console()


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
    ):
        self.llm = llm_client or get_llm_client()
        self.cache = cache_manager or CacheManager()
        self.config_manager = config_manager or get_config_manager()

        # 加载配置
        self.config = self.config_manager.load_config()
        self.prompts = self.config_manager.load_prompts()

        # 初始化 tokenizer
        try:
            self.tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo")
        except Exception:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")

        # Token 预算配置
        self.max_context = self.config.processing.max_context
        self.max_output = self.config.processing.max_output
        self.reserved_tokens = self.config.processing.reserved_tokens
        self.safety_margin = self.config.processing.safety_margin

        # 文章截取长度
        self.max_article_length = self.config.processing.max_article_length

    def count_tokens(self, text: str) -> int:
        """统计文本的 token 数量"""
        try:
            return len(self.tokenizer.encode(text))
        except Exception:
            # Fallback: 粗略估计（中文约 1.5 字符/token）
            return int(len(text) / 1.5)

    def create_batches(self, articles: List[Article]) -> List[List[Article]]:
        """智能分批：根据文章长度动态分组

        Args:
            articles: 文章列表

        Returns:
            批次列表
        """
        batches = []
        current_batch = []
        current_tokens = 0

        # 计算可用的输入 token 预算
        available_tokens = int(
            (self.max_context - self.max_output - self.reserved_tokens)
            * self.safety_margin
        )

        for article in articles:
            content = article.content
            # 根据配置截取文章长度（0 表示不截取）
            max_len = self.max_article_length if self.max_article_length > 0 else len(content)
            article_tokens = self.count_tokens(content[:max_len])

            # 检查是否需要开新批次
            if current_tokens + article_tokens > available_tokens and current_batch:
                batches.append(current_batch)
                current_batch = []
                current_tokens = 0

            current_batch.append(article)
            current_tokens += article_tokens

        # 添加最后一批
        if current_batch:
            batches.append(current_batch)

        return batches

    def format_articles_for_prompt(self, articles: List[Article]) -> str:
        """格式化文章列表用于提示词

        Args:
            articles: 文章列表

        Returns:
            格式化后的文本
        """
        articles_text = ""
        for i, article in enumerate(articles, 1):
            content = article.content
            max_len = self.max_article_length if self.max_article_length > 0 else len(content)
            # 在文章标题中加入编号，方便 LLM 引用
            articles_text += f"\n\n### [文章{i}] {article.title}\n{content[:max_len]}\n"

        return articles_text

    def _build_article_index(self, articles: List[Article]) -> Dict[int, Article]:
        """构建文章编号索引"""
        return {i: article for i, article in enumerate(articles, 1)}

    def _replace_article_refs(self, content: str, articles: List[Article]) -> str:
        """将文章引用替换为带链接的 Markdown 格式

        Args:
            content: LLM 生成的内容
            articles: 文章列表

        Returns:
            替换后的内容，引用格式为：[完整文章标题](url)
        """
        import re

        article_index = self._build_article_index(articles)

        def replace_ref(match):
            """替换文章引用为链接"""
            ref_text = match.group(0)
            numbers = re.findall(r'\d+', ref_text)
            if not numbers:
                return ref_text

            links = []
            for num_str in numbers:
                num = int(num_str)
                if num in article_index:
                    article = article_index[num]
                    url = article.url or "#"
                    # 使用完整标题，不截取
                    links.append(f"[{article.title}]({url})")

            if links:
                # 如果只有一个链接，直接返回
                if len(links) == 1:
                    return links[0]
                # 多个链接用有序列表格式
                return "\n" + "\n".join(f"{i+1}. {link}" for i, link in enumerate(links))
            return ref_text

        # 匹配括号中的引用，如 (文章1)、(文章1、2)、（文章1-3）
        pattern1 = r'[（(]文章\s*\d+(?:[、,，]\s*\d+)*\s*[）)]'
        result = re.sub(pattern1, replace_ref, content)

        # 匹配行内的引用，如 文章1、文章 1
        pattern2 = r'文章\s*\d+(?:[、,，]\s*\d+)*(?:\s*[-–—]\s*\d+)?'
        result = re.sub(pattern2, replace_ref, result)

        # 清理多余的空括号
        result = re.sub(r'[（(]\s*[）)]', '', result)

        return result

    def extract_batch_insights(
        self,
        articles: List[Article],
        topic: str,
    ) -> str:
        """从一批文章中提取核心观点

        Args:
            articles: 文章列表
            topic: 主题名称

        Returns:
            提取的核心观点（带文章引用）
        """
        # 构建输入文本
        articles_text = self.format_articles_for_prompt(articles)

        # 获取提示词
        prompt_template = self.prompts.get(topic) or self.prompts.get("general")
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

        # 带重试的 API 调用
        batch_temp = self.config.processing.batch_temperature
        return self.llm.chat(
            messages=messages,
            temperature=batch_temp,
            max_tokens=self.max_output,
        )

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

        # 带重试的最终整合
        synthesis_temp = self.config.processing.synthesis_temperature
        return self.llm.chat(
            messages=messages,
            temperature=synthesis_temp,
            max_tokens=self.max_output,
        )

    def distill_topic(
        self,
        articles: List[Article],
        topic: str,
    ) -> str:
        """蒸馏单个主题（两阶段合成）

        Args:
            articles: 该主题的所有文章
            topic: 主题名称

        Returns:
            合成后的知识文档内容（带文章引用和链接）
        """
        if not articles:
            return ""

        # 检查是否有缓存的最终结果
        cached_final = self.cache.load_final_doc(topic)
        if cached_final:
            console.print(f"[green]>> 使用缓存：【{topic}】已完成合成[/green]\n")
            # 对缓存结果也进行链接替换
            return self._replace_article_refs(cached_final, articles)

        console.print(f"\n[bold cyan]正在合成【{topic}】知识体系...[/bold cyan]")
        console.print(f"[yellow]共 {len(articles)} 篇文章[/yellow]\n")

        # 智能分批
        batches = self.create_batches(articles)
        console.print(f"[blue]智能分批：分为 {len(batches)} 批处理[/blue]")
        for i, batch in enumerate(batches, 1):
            console.print(f"  - 批次 {i}: {len(batch)} 篇文章")
        console.print()

        # 检查已完成的批次
        completed_batches = self.cache.get_completed_batches(topic, len(batches))
        if completed_batches:
            console.print(f"[yellow]>> 发现已完成的批次: {completed_batches}[/yellow]")

        # 处理每一批
        batch_insights = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("合成中...", total=len(batches))

            for i, batch in enumerate(batches):
                # 检查缓存
                if i in completed_batches:
                    cached = self.cache.load_batch_result(topic, i)
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

                    # 保存批次结果
                    self.cache.save_batch_result(topic, i, insight)

                except Exception as e:
                    console.print(f"\n[red]批次 {i + 1} 处理失败: {e}[/red]")
                    console.print("[yellow]>> 进度已保存，可使用相同命令继续[/yellow]\n")
                    raise

                progress.advance(task)

        # 最终整合
        console.print(f"[yellow]最终整合 {len(batch_insights)} 批结果...[/yellow]")
        final_doc = self.synthesize_batches(batch_insights, topic)

        # 将文章引用替换为带链接的格式
        final_doc_with_links = self._replace_article_refs(final_doc, articles)

        # 保存最终结果（保存带链接的版本）
        self.cache.save_final_doc(topic, final_doc_with_links)

        console.print(f"[green]>> 完成【{topic}】知识合成[/green]\n")
        return final_doc_with_links

    def distill_all(
        self,
        topics: Dict[str, List[Article]],
    ) -> Dict[str, KnowledgeDoc]:
        """蒸馏所有主题

        Args:
            topics: 按主题组织的文章字典

        Returns:
            每个主题的知识文档
        """
        results = {}

        for topic, articles in topics.items():
            if not articles:
                continue

            content = self.distill_topic(articles, topic)

            results[topic] = KnowledgeDoc(
                topic=topic,
                content=content,
                article_count=len(articles),
                batch_count=len(self.create_batches(articles)),
            )

        return results
