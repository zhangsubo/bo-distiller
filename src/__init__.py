"""
Bo-Distiller - 智能内容蒸馏工具

将 Cubox 收藏和本地 Markdown 文件提炼成体系化知识文档
"""

__version__ = "0.1.0"
__author__ = "Zhang Subo"

from .models import Article, SourceInfo, SystemConfig
from .config import ConfigManager, load_config, get_config_manager
from .llm_client import LLMClient, get_llm_client
from .storage import SQLiteStorage, get_storage

__all__ = [
    "Article",
    "SourceInfo",
    "SystemConfig",
    "ConfigManager",
    "load_config",
    "get_config_manager",
    "LLMClient",
    "get_llm_client",
    "SQLiteStorage",
    "get_storage",
]
