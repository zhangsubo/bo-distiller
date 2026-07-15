"""
Bo-Distiller 内容清洗模块

负责清洗文章内容，去除 HTML 标签、广告、导航等噪音。
"""

import re
from typing import Dict, List

from bs4 import BeautifulSoup
from rich.console import Console

from ..models import Article

console = Console()


class ContentCleaner:
    """内容清洗器

    清洗文章内容，去除 HTML 标签、广告、导航等噪音，
    保留正文内容。
    """

    def clean(self, article: Article) -> Article:
        """清洗单篇文章

        Args:
            article: 原始文章

        Returns:
            清洗后的文章
        """
        cleaned_content = self._clean_html(article.content)
        cleaned_title = self._clean_text(article.title)

        # 创建清洗后的文章副本
        return article.model_copy(
            update={
                "title": cleaned_title,
                "content": cleaned_content,
                "metadata": {
                    **article.metadata,
                    "cleaned": True,
                    "original_length": len(article.content),
                    "cleaned_length": len(cleaned_content),
                },
            }
        )

    def clean_batch(self, articles: List[Article]) -> List[Article]:
        """批量清洗文章

        Args:
            articles: 文章列表

        Returns:
            清洗后的文章列表
        """
        console.print("\n[bold cyan]开始清洗文章内容...[/bold cyan]\n")

        cleaned_articles = []
        for i, article in enumerate(articles, 1):
            console.print(
                f"[blue]清洗中 ({i}/{len(articles)}): {article.short_title}[/blue]"
            )
            cleaned = self.clean(article)
            cleaned_articles.append(cleaned)

        console.print(
            f"\n[bold green]>> 完成 {len(cleaned_articles)} 篇文章清洗[/bold green]\n"
        )
        return cleaned_articles

    def _clean_html(self, html_text: str) -> str:
        """去除 HTML 标签，保留纯文本

        Args:
            html_text: HTML 文本

        Returns:
            清洗后的纯文本
        """
        if not html_text:
            return ""

        # 使用 BeautifulSoup 解析
        soup = BeautifulSoup(html_text, "lxml")

        # 移除 script 和 style 标签
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        # 移除广告相关的元素
        for tag in soup.find_all(
            class_=re.compile(r"ad|advertisement|banner|sidebar", re.I)
        ):
            tag.decompose()

        # 获取纯文本
        text = soup.get_text(separator="\n")

        # 清理多余空行和空格
        text = re.sub(r"\n\s*\n", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)

        return text.strip()

    def _clean_text(self, text: str) -> str:
        """清理文本中的特殊字符

        Args:
            text: 原始文本

        Returns:
            清洗后的文本
        """
        if not text:
            return ""

        # 移除多余空格
        text = re.sub(r"\s+", " ", text)

        # 移除特殊字符（保留中英文、数字、常见标点）
        text = re.sub(
            r"[^\w\s一-鿿.,!?;:，。！？；：、（）()【】\[\]《》<>\"\'\-]+",
            "",
            text,
        )

        return text.strip()
