"""
Bo-Distiller LLM 客户端模块

支持多个 LLM 提供商（DeepSeek、Mimo、MiniMax、Kimi），
提供统一的调用接口和重试机制。
"""

import time
from typing import Callable, Dict, List, Optional

import tiktoken
from openai import OpenAI
from rich.console import Console

from .config import ConfigManager, get_config_manager
from .models import ProviderConfig

console = Console()


class LLMClient:
    """LLM 客户端 - 统一调用接口

    支持多个提供商，自动处理重试和错误。
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        config_manager: Optional[ConfigManager] = None,
    ):
        """初始化 LLM 客户端

        Args:
            provider: 提供商名称（deepseek/mimo/minimax/kimi），None 则使用默认
            config_manager: 配置管理器实例
        """
        self.config_manager = config_manager or get_config_manager()
        self.provider_config = self.config_manager.get_provider_config(provider)
        self.provider = provider or self.config_manager.load_config().llm.default_provider

        # 初始化 OpenAI 客户端
        self.client = OpenAI(
            api_key=self.provider_config.api_key,
            base_url=self.provider_config.api_base,
        )
        self.model_name = self.provider_config.model

        # 初始化 tokenizer（用于 token 计数）
        try:
            self.tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo")
        except Exception:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 8000,
        retry_count: int = 3,
    ) -> str:
        """发送对话请求

        Args:
            messages: 对话消息列表
            temperature: 温度参数
            max_tokens: 最大 token 数
            retry_count: 重试次数

        Returns:
            LLM 的回复文本
        """
        return self._call_with_retry(
            lambda: self._chat_completion(messages, temperature, max_tokens),
            retry_count=retry_count,
        )

    def _chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> str:
        """执行聊天补全"""
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"LLM API 调用失败 ({self.provider}): {e}")

    def _call_with_retry(
        self,
        func: Callable[[], str],
        retry_count: int = 3,
        initial_delay: float = 1.0,
        backoff_factor: float = 2.0,
    ) -> str:
        """带指数退避的重试机制

        Args:
            func: 要执行的函数
            retry_count: 重试次数
            initial_delay: 初始延迟（秒）
            backoff_factor: 退避因子

        Returns:
            函数执行结果
        """
        last_exception = None

        for attempt in range(retry_count):
            try:
                return func()
            except Exception as e:
                last_exception = e
                if attempt < retry_count - 1:
                    delay = initial_delay * (backoff_factor ** attempt)
                    console.print(
                        f"[yellow]API 调用失败 (尝试 {attempt + 1}/{retry_count}): {e}[/yellow]"
                    )
                    console.print(f"[yellow]等待 {delay:.1f} 秒后重试...[/yellow]")
                    time.sleep(delay)

        raise last_exception

    def count_tokens(self, text: str) -> int:
        """统计文本的 token 数量

        Args:
            text: 要统计的文本

        Returns:
            token 数量
        """
        try:
            return len(self.tokenizer.encode(text))
        except Exception:
            # Fallback: 粗略估计（中文约 1.5 字符/token）
            return int(len(text) / 1.5)

    def batch_chat(
        self,
        requests: List[Dict],
        retry_count: int = 3,
    ) -> List[str]:
        """批量调用（串行）

        Args:
            requests: 请求列表，每个请求包含 messages, temperature, max_tokens
            retry_count: 重试次数

        Returns:
            响应列表
        """
        results = []
        for i, req in enumerate(requests):
            console.print(f"[blue]处理请求 {i + 1}/{len(requests)}...[/blue]")
            result = self.chat(
                messages=req["messages"],
                temperature=req.get("temperature", 0.3),
                max_tokens=req.get("max_tokens", 8000),
                retry_count=retry_count,
            )
            results.append(result)
        return results


class LLMClientFactory:
    """LLM 客户端工厂"""

    _clients: Dict[str, LLMClient] = {}

    @classmethod
    def get_client(
        cls,
        provider: Optional[str] = None,
        config_manager: Optional[ConfigManager] = None,
    ) -> LLMClient:
        """获取 LLM 客户端实例（带缓存）

        Args:
            provider: 提供商名称
            config_manager: 配置管理器

        Returns:
            LLM 客户端实例
        """
        cache_key = provider or "default"

        if cache_key not in cls._clients:
            cls._clients[cache_key] = LLMClient(provider, config_manager)

        return cls._clients[cache_key]

    @classmethod
    def clear_cache(cls):
        """清除客户端缓存"""
        cls._clients.clear()


def get_llm_client(
    provider: Optional[str] = None,
    config_manager: Optional[ConfigManager] = None,
) -> LLMClient:
    """获取 LLM 客户端的便捷函数

    Args:
        provider: 提供商名称
        config_manager: 配置管理器

    Returns:
        LLM 客户端实例
    """
    return LLMClientFactory.get_client(provider, config_manager)
