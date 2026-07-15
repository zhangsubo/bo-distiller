"""
Bo-Distiller 内容源适配器

提供统一的接口来获取不同来源的内容。
"""

from .base import SourceAdapter
from .local_markdown import LocalMarkdownAdapter
from .cubox_adapter import CuboxAdapter
from .aggregator import ContentAggregator

__all__ = [
    "SourceAdapter",
    "LocalMarkdownAdapter",
    "CuboxAdapter",
    "ContentAggregator",
]
