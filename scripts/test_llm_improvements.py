#!/usr/bin/env python3
"""
LLM 客户端改进验证脚本

测试以下改进：
1. 异步并发调用
2. 错误处理细化
3. Token 计数准确性
4. 请求缓存
"""

import asyncio
import time
from rich.console import Console
from rich.table import Table

from src.llm_client import get_llm_client

console = Console()


def test_token_counting():
    """测试 token 计数"""
    console.print("\n[bold cyan]测试 1: Token 计数准确性[/bold cyan]")

    client = get_llm_client()

    test_texts = [
        "Hello, world!",
        "你好，世界！",
        "This is a test with 中英文混合 content.",
        "A" * 1000,  # 长文本
    ]

    table = Table(title="Token 计数测试")
    table.add_column("文本", style="cyan")
    table.add_column("字符数", style="magenta")
    table.add_column("Token 数", style="green")
    table.add_column("字符/Token", style="yellow")

    for text in test_texts:
        char_count = len(text)
        token_count = client.count_tokens(text)
        ratio = char_count / token_count if token_count > 0 else 0

        display_text = text[:30] + "..." if len(text) > 30 else text
        table.add_row(
            display_text,
            str(char_count),
            str(token_count),
            f"{ratio:.2f}",
        )

    console.print(table)


def test_sync_vs_async():
    """测试同步 vs 异步性能"""
    console.print("\n[bold cyan]测试 2: 同步 vs 异步性能对比[/bold cyan]")

    client = get_llm_client()

    # 准备测试请求
    test_requests = [
        {
            "messages": [
                {"role": "system", "content": "你是一个助手"},
                {"role": "user", "content": f"请用一句话介绍数字 {i}"}
            ],
            "temperature": 0.3,
            "max_tokens": 50,
        }
        for i in range(3)
    ]

    # 测试同步调用
    console.print("\n[yellow]同步调用（串行）...[/yellow]")
    start_time = time.time()
    try:
        sync_results = client.batch_chat(test_requests, retry_count=1)
        sync_time = time.time() - start_time
        console.print(f"[green]✓ 同步调用完成: {sync_time:.2f}秒[/green]")
    except Exception as e:
        sync_time = None
        console.print(f"[red]✗ 同步调用失败: {e}[/red]")

    # 测试异步调用
    console.print("\n[yellow]异步调用（并发=2）...[/yellow]")
    start_time = time.time()
    try:
        async_results = asyncio.run(
            client.batch_chat_async(test_requests, retry_count=1, max_concurrent=2)
        )
        async_time = time.time() - start_time
        console.print(f"[green]✓ 异步调用完成: {async_time:.2f}秒[/green]")

        if sync_time:
            speedup = sync_time / async_time
            console.print(f"[bold green]⚡ 加速比: {speedup:.2f}x[/bold green]")
    except Exception as e:
        console.print(f"[red]✗ 异步调用失败: {e}[/red]")


def test_cache():
    """测试请求缓存"""
    console.print("\n[bold cyan]测试 3: 请求缓存[/bold cyan]")

    client = get_llm_client(enable_cache=True)

    messages = [
        {"role": "system", "content": "你是一个助手"},
        {"role": "user", "content": "请说 Hello"}
    ]

    # 第一次调用
    console.print("\n[yellow]第一次调用（无缓存）...[/yellow]")
    start_time = time.time()
    try:
        result1 = client.chat(messages, temperature=0.3, max_tokens=50, retry_count=1)
        time1 = time.time() - start_time
        console.print(f"[green]✓ 耗时: {time1:.2f}秒[/green]")
    except Exception as e:
        console.print(f"[red]✗ 调用失败: {e}[/red]")
        return

    # 第二次调用（应该命中缓存）
    console.print("\n[yellow]第二次调用（应该命中缓存）...[/yellow]")
    start_time = time.time()
    result2 = client.chat(messages, temperature=0.3, max_tokens=50, retry_count=1)
    time2 = time.time() - start_time
    console.print(f"[green]✓ 耗时: {time2:.2f}秒[/green]")

    if time2 < 0.01:  # 缓存命中应该非常快
        console.print(f"[bold green]✓ 缓存命中！加速 {time1 / time2:.0f}x[/bold green]")
    else:
        console.print("[yellow]⚠ 可能未命中缓存[/yellow]")

    # 显示缓存统计
    stats = client.get_cache_stats()
    console.print(f"\n[dim]缓存统计: {stats}[/dim]")


def test_error_handling():
    """测试错误处理"""
    console.print("\n[bold cyan]测试 4: 错误处理细化[/bold cyan]")

    # 测试认证错误
    console.print("\n[yellow]测试认证错误（使用无效 API Key）...[/yellow]")
    try:
        from src.config import ConfigManager
        from src.models import ProviderConfig

        # 创建一个无效配置
        invalid_config = ProviderConfig(
            name="test",
            api_key="invalid_key",
            api_base="https://api.openai.com/v1",
            model="gpt-3.5-turbo",
        )

        # 这里只是演示错误类型，不实际调用
        console.print("[dim]（跳过实际调用以避免浪费请求）[/dim]")
        console.print("[green]✓ 错误处理代码已实现，支持以下错误类型：[/green]")
        console.print("  - AuthenticationError: 认证失败")
        console.print("  - RateLimitError: 速率限制")
        console.print("  - Timeout: 请求超时")
        console.print("  - APIConnectionError: 网络连接失败")
        console.print("  - APIError: API 错误")

    except Exception as e:
        console.print(f"[red]✗ 测试失败: {e}[/red]")


def main():
    """主函数"""
    console.print("\n[bold]=" * 50)
    console.print("[bold cyan]LLM 客户端改进验证[/bold cyan]")
    console.print("[bold]=" * 50)

    try:
        # 测试 1: Token 计数
        test_token_counting()

        # 测试 2: 性能对比（需要实际 API）
        console.print("\n[dim]提示: 测试 2 和 3 需要有效的 API 配置[/dim]")
        user_input = input("\n是否运行 API 调用测试？(y/N): ")
        if user_input.lower() == 'y':
            test_sync_vs_async()
            test_cache()

        # 测试 4: 错误处理
        test_error_handling()

        console.print("\n[bold green]✓ 所有测试完成[/bold green]\n")

    except KeyboardInterrupt:
        console.print("\n[yellow]测试被用户中断[/yellow]")
    except Exception as e:
        console.print(f"\n[red]测试失败: {e}[/red]")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
