"""
LLM 提供商元数据管理模块

从外部 API 获取提供商配置和模型列表，并缓存到数据库中。

数据来源: https://models.dev (MIT License)
API 文档: https://github.com/anomalyco/models.dev
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import aiohttp
from rich.console import Console

from .storage import get_storage

console = Console()

# LLM 元数据 API (使用 models.dev，避免 AGPL 协议风险)
LLM_METADATA_API_URL = "https://models.dev/api.json"

# 支持的提供商 ID
SUPPORTED_PROVIDERS = [
    "deepseek",
    "xiaomi",
    "xiaomi-token-plan-cn",
    "minimax",
    "moonshotai",
    "kimi-for-coding",
    "opencode-go",
]


class LLMMetadataManager:
    """LLM 元数据管理器"""

    def __init__(self):
        self.storage = get_storage()
        self.cache_duration = timedelta(days=30)  # 缓存 30 天（1 个月）

    def _get_cache_key(self, provider_id: str, data_type: str) -> str:
        """生成缓存键"""
        return f"llm_metadata_{provider_id}_{data_type}"

    def _is_cache_valid(self, cached_data: Optional[Dict]) -> bool:
        """检查缓存是否有效"""
        if not cached_data:
            return False

        cached_at = cached_data.get("cached_at")
        if not cached_at:
            return False

        try:
            cached_time = datetime.fromisoformat(cached_at)
            return datetime.now() - cached_time < self.cache_duration
        except Exception:
            return False

    async def fetch_provider_metadata(self, provider_id: str) -> Optional[Dict]:
        """从外部 API 获取提供商元数据

        从 models.dev API 获取所有提供商数据，然后提取指定提供商的信息。

        Args:
            provider_id: 提供商 ID

        Returns:
            提供商元数据字典
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(LLM_METADATA_API_URL, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        # models.dev 返回的是字典，key 是 provider_id
                        if provider_id in data:
                            provider_data = data[provider_id]
                            console.print(f"[green]✓ 获取 {provider_id} 元数据成功[/green]")
                            return provider_data
                        else:
                            console.print(
                                f"[yellow]⚠ 提供商 {provider_id} 不存在于 models.dev[/yellow]"
                            )
                            return None
                    else:
                        console.print(
                            f"[yellow]⚠ 获取元数据失败: HTTP {response.status}[/yellow]"
                        )
                        return None
        except Exception as e:
            console.print(f"[red]✗ 获取 {provider_id} 元数据失败: {e}[/red]")
            return None

    async def fetch_provider_models(
        self, provider_id: str, api_base: str, api_key: str
    ) -> Optional[List[Dict]]:
        """从提供商 API 获取模型列表

        Args:
            provider_id: 提供商 ID
            api_base: API 基础 URL
            api_key: API Key

        Returns:
            模型列表
        """
        url = f"{api_base.rstrip('/')}/v1/models"
        headers = {"Authorization": f"Bearer {api_key}"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, headers=headers, timeout=10
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        models = data.get("data", [])
                        console.print(
                            f"[green]✓ 获取 {provider_id} 模型列表成功: {len(models)} 个模型[/green]"
                        )
                        return models
                    else:
                        console.print(
                            f"[yellow]⚠ 获取 {provider_id} 模型列表失败: HTTP {response.status}[/yellow]"
                        )
                        return None
        except Exception as e:
            console.print(f"[red]✗ 获取 {provider_id} 模型列表失败: {e}[/red]")
            return None

    def get_cached_provider_metadata(self, provider_id: str) -> Optional[Dict]:
        """从缓存获取提供商元数据

        Args:
            provider_id: 提供商 ID

        Returns:
            缓存的元数据，如果无效则返回 None
        """
        cache_key = self._get_cache_key(provider_id, "metadata")
        cached_data = self.storage.get_setting(cache_key)

        if self._is_cache_valid(cached_data):
            console.print(f"[dim]>> 使用缓存: {provider_id} 元数据[/dim]")
            return cached_data.get("data")

        return None

    def get_cached_provider_models(self, provider_id: str) -> Optional[List[Dict]]:
        """从缓存获取提供商模型列表

        Args:
            provider_id: 提供商 ID

        Returns:
            缓存的模型列表，如果无效则返回 None
        """
        cache_key = self._get_cache_key(provider_id, "models")
        cached_data = self.storage.get_setting(cache_key)

        if self._is_cache_valid(cached_data):
            console.print(f"[dim]>> 使用缓存: {provider_id} 模型列表[/dim]")
            return cached_data.get("data")

        return None

    def cache_provider_metadata(self, provider_id: str, metadata: Dict):
        """缓存提供商元数据

        Args:
            provider_id: 提供商 ID
            metadata: 元数据
        """
        cache_key = self._get_cache_key(provider_id, "metadata")
        cache_data = {
            "data": metadata,
            "cached_at": datetime.now().isoformat(),
        }
        self.storage.set_setting(cache_key, cache_data)
        console.print(f"[dim]>> 已缓存 {provider_id} 元数据[/dim]")

    def cache_provider_models(self, provider_id: str, models: List[Dict]):
        """缓存提供商模型列表

        Args:
            provider_id: 提供商 ID
            models: 模型列表
        """
        cache_key = self._get_cache_key(provider_id, "models")
        cache_data = {
            "data": models,
            "cached_at": datetime.now().isoformat(),
        }
        self.storage.set_setting(cache_key, cache_data)
        console.print(f"[dim]>> 已缓存 {provider_id} 模型列表[/dim]")

    async def get_or_fetch_provider_metadata(
        self, provider_id: str, force_refresh: bool = False
    ) -> Optional[Dict]:
        """获取或刷新提供商元数据

        Args:
            provider_id: 提供商 ID
            force_refresh: 是否强制刷新

        Returns:
            提供商元数据
        """
        # 检查缓存
        if not force_refresh:
            cached = self.get_cached_provider_metadata(provider_id)
            if cached:
                return cached

        # 从 API 获取
        metadata = await self.fetch_provider_metadata(provider_id)
        if metadata:
            self.cache_provider_metadata(provider_id, metadata)
            return metadata

        # 如果 API 失败，尝试返回过期的缓存
        cache_key = self._get_cache_key(provider_id, "metadata")
        cached_data = self.storage.get_setting(cache_key)
        if cached_data:
            console.print(f"[yellow]⚠ 使用过期缓存: {provider_id} 元数据[/yellow]")
            return cached_data.get("data")

        return None

    async def get_or_fetch_provider_models(
        self,
        provider_id: str,
        api_base: str,
        api_key: str,
        force_refresh: bool = False,
    ) -> Optional[List[Dict]]:
        """获取或刷新提供商模型列表

        Args:
            provider_id: 提供商 ID
            api_base: API 基础 URL
            api_key: API Key
            force_refresh: 是否强制刷新

        Returns:
            模型列表
        """
        # 检查缓存
        if not force_refresh:
            cached = self.get_cached_provider_models(provider_id)
            if cached:
                return cached

        # 从 API 获取
        models = await self.fetch_provider_models(provider_id, api_base, api_key)
        if models:
            self.cache_provider_models(provider_id, models)
            return models

        # 如果 API 失败，尝试返回过期的缓存
        cache_key = self._get_cache_key(provider_id, "models")
        cached_data = self.storage.get_setting(cache_key)
        if cached_data:
            console.print(f"[yellow]⚠ 使用过期缓存: {provider_id} 模型列表[/yellow]")
            return cached_data.get("data")

        return None

    async def refresh_all_providers(self) -> Dict[str, bool]:
        """刷新所有支持的提供商元数据

        Returns:
            刷新结果字典 {provider_id: success}
        """
        results = {}

        for provider_id in SUPPORTED_PROVIDERS:
            metadata = await self.get_or_fetch_provider_metadata(
                provider_id, force_refresh=True
            )
            results[provider_id] = metadata is not None

        return results

    def clear_cache(self, provider_id: Optional[str] = None):
        """清除缓存

        Args:
            provider_id: 提供商 ID，None 则清除所有
        """
        if provider_id:
            # 清除指定提供商
            for data_type in ["metadata", "models"]:
                cache_key = self._get_cache_key(provider_id, data_type)
                self.storage.set_setting(cache_key, None)
            console.print(f"[green]✓ 已清除 {provider_id} 缓存[/green]")
        else:
            # 清除所有提供商
            for pid in SUPPORTED_PROVIDERS:
                self.clear_cache(pid)
            console.print("[green]✓ 已清除所有提供商缓存[/green]")


# 全局实例
_metadata_manager = None


def get_metadata_manager() -> LLMMetadataManager:
    """获取元数据管理器实例（单例）"""
    global _metadata_manager
    if _metadata_manager is None:
        _metadata_manager = LLMMetadataManager()
    return _metadata_manager
