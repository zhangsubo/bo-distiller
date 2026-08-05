import re
from typing import Dict, List, Optional

import tiktoken

from .models import Article

_tokenizer = None


def _get_tokenizer():
    global _tokenizer
    if _tokenizer is None:
        try:
            _tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo")
        except Exception:
            _tokenizer = tiktoken.get_encoding("cl100k_base")
    return _tokenizer


def count_tokens(text: str) -> int:
    try:
        return len(_get_tokenizer().encode(text))
    except Exception:
        return int(len(text) / 1.5)


def format_articles_for_prompt(
    articles: List[Article],
    max_article_length: int = 0,
) -> str:
    text = ""
    for i, article in enumerate(articles, 1):
        content = article.content
        max_len = max_article_length if max_article_length > 0 else len(content)
        text += f"\n\n### [文章{i}] {article.title}\n{content[:max_len]}\n"
    return text


def build_article_index(articles: List[Article]) -> Dict[int, Article]:
    return {i: article for i, article in enumerate(articles, 1)}


def replace_article_refs(content: str, articles: List[Article]) -> str:
    article_index = build_article_index(articles)

    def replace_ref(match):
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
                links.append(f"[{article.title}]({url})")

        if links:
            if len(links) == 1:
                return links[0]
            return "\n" + "\n".join(f"{i+1}. {link}" for i, link in enumerate(links))
        return ref_text

    pattern1 = r'[（(]文章\s*\d+(?:[、,，]\s*\d+)*\s*[）)]'
    result = re.sub(pattern1, replace_ref, content)

    pattern2 = r'文章\s*\d+(?:[、,，]\s*\d+)*(?:\s*[-–—]\s*\d+)?'
    result = re.sub(pattern2, replace_ref, result)

    result = re.sub(r'[（(]\s*[）)]', '', result)

    return result
