"""
Bo-Distiller 配置管理模块

负责加载和验证 YAML 配置文件，支持环境变量替换。
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from dotenv import load_dotenv
from rich.console import Console

from .models import (
    LLMConfig,
    OutputConfig,
    ProcessingConfig,
    ProviderConfig,
    SourceConfig,
    SystemConfig,
    TopicConfig,
    TopicDiscoveryConfig,
    PromptTemplate,
)

console = Console()

# 加载环境变量
load_dotenv(override=True)


class ConfigManager:
    """配置管理器

    负责加载 config.yaml、sources.yaml、prompts.yaml 等配置文件，
    并进行环境变量替换和 Pydantic 验证。
    """

    def __init__(self, config_dir: str = "."):
        self.config_dir = Path(config_dir)
        self._config_cache: Dict[str, Any] = {}

    def load_config(self, config_file: str = "config.yaml") -> SystemConfig:
        """加载系统配置

        Args:
            config_file: 配置文件名

        Returns:
            验证后的系统配置对象
        """
        config_path = self.config_dir / config_file

        if not config_path.exists():
            console.print(f"[yellow]警告: {config_path} 不存在，使用默认配置[/yellow]")
            return SystemConfig()

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                raw_config = yaml.safe_load(f) or {}

            # 环境变量替换
            raw_config = self._substitute_env_vars(raw_config)

            # 转换为 SystemConfig
            config = self._parse_system_config(raw_config)
            self._config_cache["system"] = config
            return config

        except Exception as e:
            console.print(f"[yellow]警告: 加载配置失败 ({e})，使用默认配置[/yellow]")
            return SystemConfig()

    def load_sources(self, sources_file: str = "sources.yaml") -> List[SourceConfig]:
        """加载内容源配置

        Args:
            sources_file: 源配置文件名

        Returns:
            内容源配置列表
        """
        sources_path = self.config_dir / sources_file

        if not sources_path.exists():
            console.print(f"[yellow]警告: {sources_path} 不存在[/yellow]")
            return []

        try:
            with open(sources_path, "r", encoding="utf-8") as f:
                raw_sources = yaml.safe_load(f) or {}

            sources_list = raw_sources.get("sources", [])
            sources = []

            for source_data in sources_list:
                # 环境变量替换
                source_data = self._substitute_env_vars(source_data)
                source = SourceConfig(**source_data)
                sources.append(source)

            self._config_cache["sources"] = sources
            return sources

        except Exception as e:
            console.print(f"[red]加载源配置失败: {e}[/red]")
            return []

    def load_prompts(self, prompts_file: str = "prompts.yaml") -> Dict[str, PromptTemplate]:
        """加载提示词配置

        Args:
            prompts_file: 提示词配置文件名

        Returns:
            提示词模板字典
        """
        prompts_path = self.config_dir / prompts_file

        if not prompts_path.exists():
            console.print(f"[yellow]警告: {prompts_path} 不存在，使用默认提示词[/yellow]")
            return self._get_default_prompts()

        try:
            with open(prompts_path, "r", encoding="utf-8") as f:
                raw_prompts = yaml.safe_load(f) or {}

            prompts = {}
            for key, value in raw_prompts.items():
                if key == "settings":
                    continue
                if isinstance(value, dict) and "system" in value:
                    prompts[key] = PromptTemplate(**value)

            self._config_cache["prompts"] = prompts
            return prompts

        except Exception as e:
            console.print(f"[yellow]警告: 加载提示词失败 ({e})，使用默认提示词[/yellow]")
            return self._get_default_prompts()

    def load_topics(self, topics_file: str = "topics.yaml") -> List[TopicConfig]:
        """加载主题配置

        Args:
            topics_file: 主题配置文件名

        Returns:
            主题配置列表
        """
        topics_path = self.config_dir / topics_file

        if not topics_path.exists():
            console.print(f"[yellow]警告: {topics_path} 不存在[/yellow]")
            return []

        try:
            with open(topics_path, "r", encoding="utf-8") as f:
                raw_topics = yaml.safe_load(f) or {}

            topics = []

            # 支持 predefined_topics 格式（键值对形式）
            predefined = raw_topics.get("predefined_topics", {})
            if predefined and isinstance(predefined, dict):
                for name, topic_data in predefined.items():
                    if isinstance(topic_data, dict):
                        topic = TopicConfig(
                            name=name,
                            keywords=topic_data.get("keywords", []),
                            prompt_key=topic_data.get("prompt_key", "general"),
                            parent=topic_data.get("parent"),
                            discovery_method=topic_data.get("discovery_method", "hybrid"),
                        )
                        topics.append(topic)

            # 兼容 topics 列表格式
            topics_list = raw_topics.get("topics", [])
            if topics_list and isinstance(topics_list, list):
                for topic_data in topics_list:
                    if isinstance(topic_data, dict):
                        topic = TopicConfig(**topic_data)
                        topics.append(topic)

            self._config_cache["topics"] = topics
            return topics

        except Exception as e:
            console.print(f"[red]加载主题配置失败: {e}[/red]")
            return []

    def _parse_system_config(self, raw_config: Dict[str, Any]) -> SystemConfig:
        """解析系统配置"""
        # 提取各部分配置
        project = raw_config.get("project", {})
        llm_raw = raw_config.get("llm", {})
        processing_raw = raw_config.get("processing", {})
        topic_raw = raw_config.get("topic_discovery", {})
        output_raw = raw_config.get("output", {})

        # 解析 LLM 配置
        providers = {}
        for name, provider_data in llm_raw.get("providers", {}).items():
            providers[name] = ProviderConfig(**provider_data)

        llm_config = LLMConfig(
            call_mode=llm_raw.get("call_mode", "direct"),
            default_provider=llm_raw.get("default_provider", "deepseek"),
            providers=providers,
        )

        # 解析处理参数
        processing_config = ProcessingConfig(**processing_raw) if processing_raw else ProcessingConfig()

        # 解析主题发现配置
        topic_config = TopicDiscoveryConfig(**topic_raw) if topic_raw else TopicDiscoveryConfig()

        # 解析输出配置
        output_config = OutputConfig(
            feishu_enabled=output_raw.get("feishu", {}).get("enabled", False),
            feishu_space_id=output_raw.get("feishu", {}).get("space_id"),
            local_enabled=output_raw.get("local", {}).get("enabled", True),
            local_dir=output_raw.get("local", {}).get("dir", "./output"),
            include_sources=output_raw.get("local", {}).get("include_sources", True),
        ) if output_raw else OutputConfig()

        return SystemConfig(
            project_name=project.get("name", "bo-distiller"),
            output_dir=project.get("output_dir", "./output"),
            cache_dir=project.get("cache_dir", ".cache"),
            llm=llm_config,
            processing=processing_config,
            topic_discovery=topic_config,
            output=output_config,
        )

    def _substitute_env_vars(self, config: Any) -> Any:
        """递归替换环境变量 ${VAR_NAME}"""
        if isinstance(config, str):
            # 替换 ${VAR_NAME} 格式
            def replace_env(match):
                var_name = match.group(1)
                return os.getenv(var_name, match.group(0))

            return re.sub(r"\$\{([^}]+)\}", replace_env, config)
        elif isinstance(config, dict):
            return {k: self._substitute_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._substitute_env_vars(item) for item in config]
        return config

    def _get_default_prompts(self) -> Dict[str, PromptTemplate]:
        """获取默认提示词"""
        return {
            "investment": PromptTemplate(
                system="你是一位资深投资分析师。请从多篇文章中提取核心投资理念和方法论。"
            ),
            "parenting": PromptTemplate(
                system="你是一位教育专家。请从多篇文章中提取育儿理念和方法。"
            ),
            "personal_growth": PromptTemplate(
                system="你是一位人生导师。请从多篇文章中提取个人成长智慧。"
            ),
            "general": PromptTemplate(
                system="你是一位知识整理专家。请从多篇文章中提取核心观点和见解。"
            ),
            "synthesis": PromptTemplate(
                system="你是知识整合专家，擅长将分散的观点整合成体系化文档。",
                user_template="我从多批文章中提取了核心观点，现在需要你整合成一份完整、系统的文档。\n\n以下是 {batch_count} 批提取结果：",
            ),
        }

    def get_provider_config(self, provider_name: Optional[str] = None) -> ProviderConfig:
        """获取指定提供商的配置

        Args:
            provider_name: 提供商名称，None 则使用默认

        Returns:
            提供商配置
        """
        config = self._config_cache.get("system")
        if not config:
            config = self.load_config()

        provider = provider_name or config.llm.default_provider

        if provider not in config.llm.providers:
            raise ValueError(f"未找到提供商配置: {provider}")

        return config.llm.providers[provider]

    def get_cache_dir(self) -> Path:
        """获取缓存目录路径"""
        config = self._config_cache.get("system")
        if not config:
            config = self.load_config()

        cache_dir = Path(config.cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    def get_output_dir(self) -> Path:
        """获取输出目录路径"""
        config = self._config_cache.get("system")
        if not config:
            config = self.load_config()

        output_dir = Path(config.output.local_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir


# 全局配置管理器实例
_config_manager: Optional[ConfigManager] = None


def get_config_manager(config_dir: str = ".") -> ConfigManager:
    """获取全局配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager(config_dir)
    return _config_manager


def load_config(config_dir: str = ".") -> SystemConfig:
    """加载系统配置的便捷函数"""
    return get_config_manager(config_dir).load_config()
