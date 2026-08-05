#!/usr/bin/env python3
"""
LLM 元数据管理功能测试脚本

测试以下功能：
1. 获取支持的提供商列表
2. 获取提供商元数据
3. 获取提供商模型列表
4. 缓存管理
"""

import asyncio
from rich.console import Console
from rich.table import Table

from src.llm_metadata import get_metadata_manager, SUPPORTED_PROVIDERS

console = Console()


async def test_get_providers():
    """测试获取提供商列表"""
    console.print("\n[bold cyan]测试 1: 获取支持的提供商列表[/bold cyan]")

    table = Table(title="支持的提供商")
    table.add_column("序号", style="cyan")
    table.add_column("提供商 ID", style="green")

    for i, provider_id in enumerate(SUPPORTED_PROVIDERS, 1):
        table.add_row(str(i), provider_id)

    console.print(table)
    console.print(f"[green]✓ 共支持 {len(SUPPORTED_PROVIDERS)} 个提供商[/green]")


async def test_get_metadata():
    """测试获取提供商元数据"""
    console.print("\n[bold cyan]测试 2: 获取提供商元数据[/bold cyan]")

    manager = get_metadata_manager()

    # 测试获取第一个提供商的元数据
    provider_id = SUPPORTED_PROVIDERS[0]
    console.print(f"\n[yellow]获取 {provider_id} 元数据...[/yellow]")

    try:
        metadata = await manager.get_or_fetch_provider_metadata(provider_id)

        if metadata:
            console.print(f"[green]✓ 成功获取 {provider_id} 元数据[/green]")
            console.print(f"  名称: {metadata.get('name', 'N/A')}")
            console.print(f"  Base URL: {metadata.get('base_url', 'N/A')}")
            console.print(f"  描述: {metadata.get('description', 'N/A')[:100]}...")

            models = metadata.get('models', [])
            console.print(f"  模型数量: {len(models)}")
            if models:
                console.print(f"  示例模型: {models[0] if isinstance(models[0], str) else models[0].get('id', 'N/A')}")
        else:
            console.print(f"[red]✗ 无法获取 {provider_id} 元数据[/red]")

    except Exception as e:
        console.print(f"[red]✗ 获取元数据失败: {e}[/red]")


async def test_cache():
    """测试缓存功能"""
    console.print("\n[bold cyan]测试 3: 缓存功能[/bold cyan]")

    manager = get_metadata_manager()
    provider_id = SUPPORTED_PROVIDERS[0]

    # 第一次获取（从 API）
    console.print(f"\n[yellow]第一次获取 {provider_id} 元数据（从 API）...[/yellow]")
    import time
    start = time.time()
    metadata1 = await manager.get_or_fetch_provider_metadata(provider_id, force_refresh=True)
    time1 = time.time() - start
    console.print(f"[green]✓ 耗时: {time1:.2f}秒[/green]")

    # 第二次获取（从缓存）
    console.print(f"\n[yellow]第二次获取 {provider_id} 元数据（从缓存）...[/yellow]")
    start = time.time()
    metadata2 = await manager.get_or_fetch_provider_metadata(provider_id, force_refresh=False)
    time2 = time.time() - start
    console.print(f"[green]✓ 耗时: {time2:.2f}秒[/green]")

    if time2 < 0.1:
        console.print(f"[bold green]✓ 缓存命中！加速 {time1 / time2:.0f}x[/bold green]")
    else:
        console.print("[yellow]⚠ 可能未命中缓存[/yellow]")


async def test_cache_stats():
    """测试缓存统计"""
    console.print("\n[bold cyan]测试 4: 缓存统计[/bold cyan]")

    manager = get_metadata_manager()

    table = Table(title="缓存状态")
    table.add_column("提供商 ID", style="cyan")
    table.add_column("元数据缓存", style="green")
    table.add_column("模型缓存", style="yellow")

    for provider_id in SUPPORTED_PROVIDERS[:3]:  # 只检查前 3 个
        metadata_cached = manager.get_cached_provider_metadata(provider_id) is not None
        models_cached = manager.get_cached_provider_models(provider_id) is not None

        table.add_row(
            provider_id,
            "✓" if metadata_cached else "✗",
            "✓" if models_cached else "✗",
        )

    console.print(table)


async def test_refresh_all():
    """测试刷新所有提供商"""
    console.print("\n[bold cyan]测试 5: 刷新所有提供商元数据[/bold cyan]")

    user_input = input("\n是否刷新所有提供商元数据？这可能需要一些时间。(y/N): ")
    if user_input.lower() != 'y':
        console.print("[yellow]跳过刷新测试[/yellow]")
        return

    manager = get_metadata_manager()

    console.print("\n[yellow]开始刷新所有提供商...[/yellow]")
    results = await manager.refresh_all_providers()

    table = Table(title="刷新结果")
    table.add_column("提供商 ID", style="cyan")
    table.add_column("状态", style="green")

    for provider_id, success in results.items():
        table.add_row(
            provider_id,
            "✓ 成功" if success else "✗ 失败",
        )

    console.print(table)

    success_count = sum(1 for v in results.values() if v)
    total_count = len(results)
    console.print(f"\n[green]✓ 刷新完成: {success_count}/{total_count} 成功[/green]")


async def main():
    """主函数"""
    console.print("\n[bold]=" * 50)
    console.print("[bold cyan]LLM 元数据管理功能测试[/bold cyan]")
    console.print("[bold]=" * 50)

    try:
        # 测试 1: 获取提供商列表
        await test_get_providers()

        # 测试 2: 获取元数据
        await test_get_metadata()

        # 测试 3: 缓存功能
        await test_cache()

        # 测试 4: 缓存统计
        await test_cache_stats()

        # 测试 5: 刷新所有
        await test_refresh_all()

        console.print("\n[bold green]✓ 所有测试完成[/bold green]\n")

    except KeyboardInterrupt:
        console.print("\n[yellow]测试被用户中断[/yellow]")
    except Exception as e:
        console.print(f"\n[red]测试失败: {e}[/red]")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
