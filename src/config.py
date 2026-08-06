"""
Bo-Distiller 配置管理模块

负责加载和验证配置，支持从 SQLite 数据库存储。
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from dotenv import load_dotenv
from rich.console import Console

from .models import (
    DatabaseConfig,
    LLMConfig,
    OutputConfig,
    ProcessingConfig,
    ProviderConfig,
    SourceConfig,
    SyncConfig,
    SystemConfig,
    TopicConfig,
    TopicDiscoveryConfig,
    PromptTemplate,
)
from .storage import get_storage

console = Console()

load_dotenv(override=True)

SETTING_KEYS = {
    "system": "system_config",
    "sources": "sources",
    "prompts": "prompts",
    "topics": "topics",
}


class ConfigManager:
    def __init__(self, config_dir: str = "."):
        self.config_dir = Path(config_dir)
        self._config_cache: Dict[str, Any] = {}
        self._storage = get_storage()

    def _migrate_yaml_to_db(self, key: str, yaml_file: str) -> Optional[Dict]:
        yaml_path = self.config_dir / yaml_file
        if not yaml_path.exists():
            return None
        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            if data:
                self._storage.set_setting(key, data)
                console.print(f"[dim]>> 迁移 {yaml_file} 到数据库[/dim]")
            return data
        except Exception as e:
            console.print(f"[yellow]迁移 {yaml_file} 失败: {e}[/yellow]")
            return None

    def load_config(self, config_file: str = "config.yaml") -> SystemConfig:
        db_key = SETTING_KEYS["system"]
        raw_config = self._storage.get_setting(db_key)
        if raw_config is None:
            raw_config = self._migrate_yaml_to_db(db_key, config_file)
        if not raw_config:
            return SystemConfig()
        try:
            raw_config = self._substitute_env_vars(raw_config)
            config = self._parse_system_config(raw_config)
            self._validate_config(config)
            self._config_cache["system"] = config
            return config
        except Exception as e:
            console.print(f"[red]配置加载失败: {e}[/red]")
            return SystemConfig()

    def save_config(self, config: Dict) -> None:
        self._storage.set_setting(SETTING_KEYS["system"], config)
        self._config_cache.pop("system", None)

    def load_sources(self, sources_file: str = "sources.yaml") -> List[SourceConfig]:
        db_key = SETTING_KEYS["sources"]
        raw_sources = self._storage.get_setting(db_key)
        if raw_sources is None:
            raw_sources = self._migrate_yaml_to_db(db_key, sources_file)
        if not raw_sources:
            return []
        try:
            sources_list = raw_sources.get("sources", [])
            sources = []
            for source_data in sources_list:
                source_data = self._substitute_env_vars(source_data)
                source = SourceConfig(**source_data)
                sources.append(source)
            self._config_cache["sources"] = sources
            return sources
        except Exception as e:
            console.print(f"[red]加载源配置失败: {e}[/red]")
            return []

    def save_sources(self, sources: List[Dict]) -> None:
        self._storage.set_setting(SETTING_KEYS["sources"], {"sources": sources})
        self._config_cache.pop("sources", None)

    def load_prompts(self, prompts_file: str = "prompts.yaml") -> Dict[str, PromptTemplate]:
        db_key = SETTING_KEYS["prompts"]
        raw_prompts = self._storage.get_setting(db_key)
        if raw_prompts is None:
            raw_prompts = self._migrate_yaml_to_db(db_key, prompts_file)
        if not raw_prompts:
            return self._get_default_prompts()
        try:
            prompts = {}
            for key, value in raw_prompts.items():
                if key == "settings":
                    continue
                if isinstance(value, dict) and "system" in value:
                    prompts[key] = PromptTemplate(**value)
            self._config_cache["prompts"] = prompts
            return prompts
        except Exception as e:
            console.print(f"[yellow]加载提示词失败 ({e})，使用默认提示词[/yellow]")
            return self._get_default_prompts()

    def save_prompts(self, prompts: Dict) -> None:
        self._storage.set_setting(SETTING_KEYS["prompts"], prompts)
        self._config_cache.pop("prompts", None)

    def load_topics(self, topics_file: str = "topics.yaml") -> List[TopicConfig]:
        db_key = SETTING_KEYS["topics"]
        raw_topics = self._storage.get_setting(db_key)
        if raw_topics is None:
            raw_topics = self._migrate_yaml_to_db(db_key, topics_file)
        if not raw_topics:
            return []
        try:
            topics = []
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

    def save_topics(self, topics: Dict) -> None:
        self._storage.set_setting(SETTING_KEYS["topics"], topics)
        self._config_cache.pop("topics", None)

    def _parse_system_config(self, raw_config: Dict[str, Any]) -> SystemConfig:
        """解析系统配置"""
        # 提取各部分配置
        project = raw_config.get("project", {})
        database_raw = raw_config.get("database", {})
        llm_raw = raw_config.get("llm", {})
        processing_raw = raw_config.get("processing", {})
        topic_raw = raw_config.get("topic_discovery", {})
        output_raw = raw_config.get("output", {})
        sync_raw = raw_config.get("sync", {})

        # 解析数据库配置（优先从环境变量读取）
        from .models import DatabaseConfig

        # 从环境变量读取数据库类型
        db_type = os.getenv("DATABASE_TYPE", database_raw.get("type", "sqlite"))

        # 准备数据库配置
        db_config_dict = {
            "type": db_type,
            "sqlite": database_raw.get("sqlite", {"path": "./data/distiller.db"}),
            "mysql": database_raw.get("mysql", {
                "host": "127.0.0.1",
                "port": 3306,
                "user": "root",
                "password": "",
                "database": "distill"
            })
        }

        # 从环境变量覆盖 SQLite 配置
        if db_type == "sqlite":
            sqlite_path = os.getenv("SQLITE_DB_PATH")
            if sqlite_path:
                db_config_dict["sqlite"]["path"] = sqlite_path

        # 从环境变量覆盖 MySQL 配置
        if db_type == "mysql":
            if os.getenv("MYSQL_HOST"):
                db_config_dict["mysql"]["host"] = os.getenv("MYSQL_HOST")
            if os.getenv("MYSQL_PORT"):
                db_config_dict["mysql"]["port"] = int(os.getenv("MYSQL_PORT"))
            if os.getenv("MYSQL_USER"):
                db_config_dict["mysql"]["user"] = os.getenv("MYSQL_USER")
            if os.getenv("MYSQL_PASSWORD"):
                db_config_dict["mysql"]["password"] = os.getenv("MYSQL_PASSWORD")
            if os.getenv("MYSQL_DATABASE"):
                db_config_dict["mysql"]["database"] = os.getenv("MYSQL_DATABASE")

        database_config = DatabaseConfig(**db_config_dict)

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

        # 解析定时同步配置
        sync_config = SyncConfig(**sync_raw) if sync_raw else SyncConfig()

        return SystemConfig(
            project_name=project.get("name", "bo-distiller"),
            output_dir=project.get("output_dir", "./output"),
            cache_dir=project.get("cache_dir", ".cache"),
            database=database_config,
            llm=llm_config,
            processing=processing_config,
            topic_discovery=topic_config,
            output=output_config,
            sync=sync_config,
        )

    def _substitute_env_vars(self, config: Any) -> Any:
        """递归替换环境变量

        支持格式:
        - ${VAR_NAME} - 使用环境变量，不存在则保留原始字符串
        - ${VAR_NAME:-default} - 使用环境变量，不存在则使用默认值
        """
        if isinstance(config, str):
            def replace_env(match):
                var_spec = match.group(1)
                # 支持 ${VAR:-default} 语法
                if ':-' in var_spec:
                    var_name, default = var_spec.split(':-', 1)
                    return os.getenv(var_name, default)
                else:
                    var_name = var_spec
                    value = os.getenv(var_name)
                    if value is None:
                        # 保留原始占位符以便识别未解析的变量
                        return match.group(0)
                    return value

            return re.sub(r"\$\{([^}]+)\}", replace_env, config)
        elif isinstance(config, dict):
            return {k: self._substitute_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._substitute_env_vars(item) for item in config]
        return config

    def _validate_config(self, config: SystemConfig) -> None:
        """验证配置完整性和一致性

        Raises:
            ValueError: 配置不一致或缺少必需项
        """
        # 检查飞书配置
        if config.output.feishu_enabled and not config.output.feishu_space_id:
            raise ValueError("启用飞书输出但未配置 space_id")

        # 移除对所有提供商的验证，只在实际使用时验证

        # 检查默认提供商存在性
        if config.llm.default_provider not in config.llm.providers:
            raise ValueError(f"默认提供商 {config.llm.default_provider} 未定义")

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

        Raises:
            ValueError: 提供商不存在
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


# 支持多配置目录的全局配置管理器
_config_managers: Dict[str, ConfigManager] = {}


def get_config_manager(config_dir: str = ".") -> ConfigManager:
    """获取配置管理器实例

    支持多配置目录，每个目录维护独立的配置管理器实例。

    Args:
        config_dir: 配置目录路径

    Returns:
        配置管理器实例
    """
    abs_dir = str(Path(config_dir).resolve())
    if abs_dir not in _config_managers:
        _config_managers[abs_dir] = ConfigManager(abs_dir)
    return _config_managers[abs_dir]


def load_config(config_dir: str = ".") -> SystemConfig:
    """加载系统配置的便捷函数"""
    return get_config_manager(config_dir).load_config()
