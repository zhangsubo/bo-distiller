"""
Bo-Distiller LLM 客户端模块

支持多个 LLM 提供商（DeepSeek、Mimo、MiniMax、Kimi），
提供统一的调用接口和重试机制。

改进点：
- 支持异步并发调用
- 细化错误类型处理
- 修复 token 计数
- 添加请求级缓存
"""

import asyncio
import hashlib
import json
import time
from typing import Callable, Dict, List, Optional

from openai import (
    OpenAI,
    AsyncOpenAI,
    APIError,
    RateLimitError,
    Timeout,
    AuthenticationError,
    APIConnectionError,
)
from rich.console import Console

from .config import ConfigManager, get_config_manager
from .models import ProviderConfig

console = Console()


class LLMClient:
    """LLM 客户端 - 统一调用接口

    支持多个提供商，自动处理重试和错误。
    支持同步和异步调用模式。
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        config_manager: Optional[ConfigManager] = None,
        enable_cache: bool = True,
    ):
        """初始化 LLM 客户端

        Args:
            provider: 提供商名称（deepseek/mimo/minimax/kimi），None 则使用默认
            config_manager: 配置管理器实例
            enable_cache: 是否启用请求级缓存
        """
        self.config_manager = config_manager or get_config_manager()
        self.provider_config = self.config_manager.get_provider_config(provider)
        self.provider = provider or self.config_manager.load_config().llm.default_provider

        # 初始化同步和异步客户端
        self.client = OpenAI(
            api_key=self.provider_config.api_key,
            base_url=self.provider_config.api_base,
            timeout=60.0,  # 添加超时控制
            max_retries=0,  # 自己控制重试逻辑
        )

        self.async_client = AsyncOpenAI(
            api_key=self.provider_config.api_key,
            base_url=self.provider_config.api_base,
            timeout=60.0,
            max_retries=0,
        )

        self.model_name = self.provider_config.model

        # 初始化 tokenizer
        self._init_tokenizer()

        # 请求缓存
        self.enable_cache = enable_cache
        self._cache: Dict[str, str] = {}

    def _init_tokenizer(self):
        """初始化 tokenizer"""
        try:
            import tiktoken
            # 尝试使用 GPT-4 的 tokenizer（适用于大部分模型）
            self.tokenizer = tiktoken.encoding_for_model("gpt-4")
        except Exception:
            console.print("[yellow]无法加载 tiktoken，将使用估算方法[/yellow]")
            self.tokenizer = None

    def _get_cache_key(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> str:
        """生成请求缓存 key"""
        content = json.dumps(
            {
                "messages": messages,
                "temp": temperature,
                "max": max_tokens,
                "model": self.model_name,
            },
            sort_keys=True,
            ensure_ascii=False,
        )
        return hashlib.md5(content.encode()).hexdigest()

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 8000,
        retry_count: int = 3,
    ) -> str:
        """发送对话请求（同步版本）

        Args:
            messages: 对话消息列表
            temperature: 温度参数
            max_tokens: 最大 token 数
            retry_count: 重试次数

        Returns:
            LLM 的回复文本
        """
        # 检查缓存
        if self.enable_cache:
            cache_key = self._get_cache_key(messages, temperature, max_tokens)
            if cache_key in self._cache:
                console.print("[dim]>> 使用请求缓存[/dim]")
                return self._cache[cache_key]

        result = self._call_with_retry(
            lambda: self._chat_completion(messages, temperature, max_tokens),
            retry_count=retry_count,
        )

        # 写入缓存
        if self.enable_cache:
            self._cache[cache_key] = result

        return result

    async def chat_async(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 8000,
        retry_count: int = 3,
    ) -> str:
        """发送对话请求（异步版本）

        Args:
            messages: 对话消息列表
            temperature: 温度参数
            max_tokens: 最大 token 数
            retry_count: 重试次数

        Returns:
            LLM 的回复文本
        """
        # 检查缓存
        if self.enable_cache:
            cache_key = self._get_cache_key(messages, temperature, max_tokens)
            if cache_key in self._cache:
                console.print("[dim]>> 使用请求缓存[/dim]")
                return self._cache[cache_key]

        result = await self._call_with_retry_async(
            lambda: self._chat_completion_async(messages, temperature, max_tokens),
            retry_count=retry_count,
        )

        # 写入缓存
        if self.enable_cache:
            self._cache[cache_key] = result

        return result

    def _chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> str:
        """执行聊天补全（同步）"""
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content
        except AuthenticationError as e:
            raise Exception(f"认证失败 ({self.provider}): 请检查 API Key")
        except RateLimitError as e:
            raise Exception(f"速率限制 ({self.provider}): {e}")
        except Timeout as e:
            raise Exception(f"请求超时 ({self.provider}): {e}")
        except APIConnectionError as e:
            raise Exception(f"网络连接失败 ({self.provider}): {e}")
        except APIError as e:
            raise Exception(f"API 错误 ({self.provider}): {e}")
        except Exception as e:
            raise Exception(f"未知错误 ({self.provider}): {e}")

    async def _chat_completion_async(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> str:
        """执行聊天补全（异步）"""
        try:
            response = await self.async_client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content
        except AuthenticationError as e:
            raise Exception(f"认证失败 ({self.provider}): 请检查 API Key")
        except RateLimitError as e:
            raise Exception(f"速率限制 ({self.provider}): {e}")
        except Timeout as e:
            raise Exception(f"请求超时 ({self.provider}): {e}")
        except APIConnectionError as e:
            raise Exception(f"网络连接失败 ({self.provider}): {e}")
        except APIError as e:
            raise Exception(f"API 错误 ({self.provider}): {e}")
        except Exception as e:
            raise Exception(f"未知错误 ({self.provider}): {e}")

    def _call_with_retry(
        self,
        func: Callable[[], str],
        retry_count: int = 3,
        initial_delay: float = 1.0,
        backoff_factor: float = 2.0,
    ) -> str:
        """带指数退避的重试机制（同步）

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

    async def _call_with_retry_async(
        self,
        func: Callable,
        retry_count: int = 3,
        initial_delay: float = 1.0,
        backoff_factor: float = 2.0,
    ) -> str:
        """带指数退避的重试机制（异步）

        Args:
            func: 要执行的异步函数
            retry_count: 重试次数
            initial_delay: 初始延迟（秒）
            backoff_factor: 退避因子

        Returns:
            函数执行结果
        """
        last_exception = None

        for attempt in range(retry_count):
            try:
                return await func()
            except Exception as e:
                last_exception = e
                if attempt < retry_count - 1:
                    delay = initial_delay * (backoff_factor ** attempt)
                    console.print(
                        f"[yellow]API 调用失败 (尝试 {attempt + 1}/{retry_count}): {e}[/yellow]"
                    )
                    console.print(f"[yellow]等待 {delay:.1f} 秒后重试...[/yellow]")
                    await asyncio.sleep(delay)

        raise last_exception

    def count_tokens(self, text: str) -> int:
        """统计文本的 token 数量

        Args:
            text: 待统计的文本

        Returns:
            token 数量
        """
        if self.tokenizer:
            try:
                return len(self.tokenizer.encode(text))
            except Exception:
                pass

        # Fallback: 更保守的估算（中文约 2.5 字符/token，英文约 4 字符/token）
        # 混合文本使用 2.5 作为平衡值
        return int(len(text) / 2.5)

    def batch_chat(
        self,
        requests: List[Dict],
        retry_count: int = 3,
    ) -> List[str]:
        """批量调用（串行，保持向后兼容）

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

    async def batch_chat_async(
        self,
        requests: List[Dict],
        retry_count: int = 3,
        max_concurrent: int = 3,
    ) -> List[str]:
        """批量调用（异步并发，新方法）

        Args:
            requests: 请求列表，每个请求包含 messages, temperature, max_tokens
            retry_count: 重试次数
            max_concurrent: 最大并发数

        Returns:
            响应列表
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def _call_with_sem(i: int, req: Dict) -> str:
            async with semaphore:
                console.print(f"[blue]处理请求 {i + 1}/{len(requests)}...[/blue]")
                return await self.chat_async(
                    messages=req["messages"],
                    temperature=req.get("temperature", 0.3),
                    max_tokens=req.get("max_tokens", 8000),
                    retry_count=retry_count,
                )

        tasks = [_call_with_sem(i, req) for i, req in enumerate(requests)]
        return await asyncio.gather(*tasks)

    def clear_cache(self):
        """清除请求缓存"""
        self._cache.clear()
        console.print("[dim]>> 已清除请求缓存[/dim]")

    def get_cache_stats(self) -> Dict[str, int]:
        """获取缓存统计信息"""
        return {
            "size": len(self._cache),
            "enabled": self.enable_cache,
        }


_clients: Dict[str, LLMClient] = {}


def get_llm_client(
    provider: Optional[str] = None,
    config_manager: Optional[ConfigManager] = None,
    enable_cache: bool = True,
) -> LLMClient:
    """获取 LLM 客户端实例（单例模式）

    Args:
        provider: 提供商名称
        config_manager: 配置管理器
        enable_cache: 是否启用缓存

    Returns:
        LLMClient 实例
    """
    cache_key = provider or "default"
    if cache_key not in _clients:
        _clients[cache_key] = LLMClient(provider, config_manager, enable_cache)
    return _clients[cache_key]


def clear_all_clients():
    """清除所有客户端实例"""
    _clients.clear()
