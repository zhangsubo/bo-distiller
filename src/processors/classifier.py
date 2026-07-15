"""
Bo-Distiller 主题分类模块

基于关键词的主题分类，支持从配置文件加载分类规则。
"""

from typing import Dict, List, Optional

import yaml
from pathlib import Path
from rich.console import Console

from ..config import ConfigManager, get_config_manager
from ..models import Article, TopicConfig

console = Console()


class TopicClassifier:
    """主题分类器

    基于关键词匹配对文章进行分类。
    """

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        self.config_manager = config_manager or get_config_manager()
        self.topics = self._load_topics()

    def _load_topics(self) -> List[TopicConfig]:
        """加载主题配置"""
        topics = self.config_manager.load_topics()

        # 如果没有配置主题，使用默认主题
        if not topics:
            topics = self._get_default_topics()

        return topics

    def _get_default_topics(self) -> List[TopicConfig]:
        """获取默认主题配置"""
        return [
            TopicConfig(
                name="技术",
                keywords=["Python", "JavaScript", "Docker", "API", "架构", "数据库", "前端", "后端", "AI", "机器学习"],
                prompt_key="tech",
            ),
            TopicConfig(
                name="产品",
                keywords=["产品", "用户", "需求", "设计", "体验", "迭代", "MVP"],
                prompt_key="product",
            ),
            TopicConfig(
                name="思考",
                keywords=["思考", "认知", "成长", "学习", "方法论", "思维", "决策"],
                prompt_key="thinking",
            ),
        ]

    def classify(self, article: Article) -> str:
        """对单篇文章分类

        Args:
            article: 文章

        Returns:
            主题名称
        """
        text = f"{article.title} {article.content[:500]}"

        # 计算每个主题的匹配分数
        scores: Dict[str, int] = {}
        for topic in self.topics:
            score = sum(1 for kw in topic.keywords if kw.lower() in text.lower())
            if score > 0:
                scores[topic.name] = score

        # 返回得分最高的主题
        if scores:
            return max(scores, key=scores.get)

        return "其他"

    def _is_excluded(self, article: Article) -> bool:
        """检查文章是否应该被排除

        当前不排除任何文章
        """
        return False

    def classify_batch(self, articles: List[Article]) -> Dict[str, List[Article]]:
        """批量分类文章

        Args:
            articles: 文章列表

        Returns:
            按主题组织的文章字典
        """
        console.print("\n[bold cyan]开始主题分类...[/bold cyan]\n")

        # 过滤排除的文章
        filtered_articles = []
        excluded_count = 0
        for article in articles:
            if self._is_excluded(article):
                excluded_count += 1
            else:
                filtered_articles.append(article)

        if excluded_count > 0:
            console.print(f"[yellow]>> 排除数据资产类文章 {excluded_count} 篇[/yellow]\n")

        # 初始化分类结果
        categorized: Dict[str, List[Article]] = {topic.name: [] for topic in self.topics}
        categorized["其他"] = []

        # 分类每篇文章
        for article in filtered_articles:
            topic = self.classify(article)
            categorized[topic].append(article)

        # 打印统计
        console.print("[bold]分类统计：[/bold]")
        for topic, items in categorized.items():
            if items:
                console.print(f"  - {topic}: {len(items)} 篇")

        # 移除空分类
        categorized = {k: v for k, v in categorized.items() if v}

        console.print()
        return categorized
