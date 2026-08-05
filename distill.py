#!/usr/bin/env python3
"""
Bo-Distiller - 主程序入口

用法:
    python distill.py run              # 完整流程（增量模式）
    python distill.py run --full       # 完整流程（全量模式）
    python distill.py run --limit 10   # 测试模式（只处理10篇）

    python distill.py sources add --cubox
    python distill.py sources list
"""

import sys
from pathlib import Path

import click
from rich.console import Console

sys.path.insert(0, str(Path(__file__).parent))

from src.adapters.aggregator import ContentAggregator
from src.cache import CacheManager
from src.config import get_config_manager
from src.orchestrator import run_distillation

console = Console()

__version__ = "0.2.0"


@click.group()
@click.version_option(version=__version__)
def cli():
    """Bo-Distiller - 智能内容蒸馏工具"""
    pass


@cli.command()
@click.option('--incremental/--full', default=True, help='增量/全量模式（默认增量）')
@click.option('--limit', type=int, default=None, help='限制处理的文章数量（测试用）')
@click.option('--model', type=click.Choice(['deepseek', 'mimo', 'minimax', 'kimi']),
              default='deepseek', help='选择 LLM 模型')
@click.option('--clear-cache', is_flag=True, help='清除所有缓存后退出')
def run(incremental: bool, limit: int, model: str, clear_cache: bool):
    """运行完整蒸馏流程"""
    config_manager = get_config_manager()
    config = config_manager.load_config()
    cache = CacheManager(config.cache_dir)

    if clear_cache:
        cache.clear_cache()
        console.print("[green]>> 缓存已清除[/green]")
        return

    mode = "增量" if incremental else "全量"
    console.print(f"\n[bold magenta]═══════════════════════════════════════[/bold magenta]")
    console.print(f"[bold magenta]    Bo-Distiller v{__version__}[/bold magenta]")
    console.print(f"[bold magenta]    智能内容蒸馏 · {mode}模式[/bold magenta]")
    console.print(f"[bold magenta]═══════════════════════════════════════[/bold magenta]\n")

    try:
        console.print("[bold]步骤 1/5: 获取文章[/bold]")
        run_distillation(
            config_manager=config_manager,
            cache=cache,
            model=model,
            incremental=incremental,
            limit=limit,
            console=console,
        )
    except KeyboardInterrupt:
        console.print("\n[yellow]>> 用户中断，进度已保存[/yellow]")
    except Exception as e:
        console.print(f"\n[red]>> 错误: {e}[/red]")
        raise


@cli.group()
def sources():
    """内容源管理"""
    pass


@sources.command()
@click.option('--cubox', is_flag=True, help='添加 Cubox 源')
@click.option('--folder', type=click.Path(exists=True), help='添加本地 Markdown 文件夹')
def add(cubox: bool, folder: str):
    """添加内容源"""

    if cubox:
        console.print("[yellow]Cubox 源添加功能待实现...[/yellow]")
        console.print("[dim]提示: 确保已安装并配置 Cubox CLI[/dim]")

    if folder:
        console.print(f"[yellow]添加本地文件夹: {folder}[/yellow]")
        console.print("[yellow]功能待实现...[/yellow]")


@sources.command()
def list():
    """列出所有内容源及其状态"""
    config_manager = get_config_manager()
    aggregator = ContentAggregator(config_manager)
    aggregator.print_sources_status()


@cli.command()
@click.option('--incremental/--full', default=True, help='增量/全量抓取')
def fetch(incremental: bool):
    """抓取内容（不执行蒸馏）"""
    config_manager = get_config_manager()
    config = config_manager.load_config()
    cache = CacheManager(config.cache_dir)
    aggregator = ContentAggregator(config_manager)

    mode = "增量" if incremental else "全量"
    console.print(f"\n[bold]开始 {mode} 抓取...[/bold]\n")

    articles = aggregator.fetch_all(incremental=incremental)

    if articles:
        cache.save_articles(articles)
        console.print(f"[green]抓取完成：{len(articles)} 篇文章已保存到缓存[/green]")
    else:
        console.print("[yellow]未获取到任何文章[/yellow]")


@cli.command()
@click.option('--feishu', is_flag=True, help='输出到飞书知识库')
@click.option('--local', is_flag=True, help='输出到本地 Markdown')
@click.option('--all', 'output_all', is_flag=True, help='输出到所有已启用的目标')
def output(feishu: bool, local: bool, output_all: bool):
    """生成输出（使用缓存的蒸馏结果）"""
    
    if output_all:
        console.print("[yellow]输出到所有目标...[/yellow]")
    elif feishu:
        console.print("[yellow]输出到飞书知识库...[/yellow]")
    elif local:
        console.print("[yellow]输出到本地 Markdown...[/yellow]")
    else:
        console.print("[red]请指定输出目标: --feishu, --local 或 --all[/red]")
        return
    
    console.print("[yellow]功能待实现...[/yellow]")


@cli.command()
def status():
    """显示项目整体状态"""
    from rich.table import Table

    config_manager = get_config_manager()
    config = config_manager.load_config()
    cache = CacheManager(config.cache_dir)
    cache_info = cache.get_cache_info()

    table = Table(title="Bo-Distiller 状态")
    table.add_column("项目", style="cyan")
    table.add_column("状态", style="green")

    table.add_row("版本", __version__)
    table.add_row("开发阶段", "✅ 核心功能完成")
    table.add_row("设计文档", "✅ 完成")
    table.add_row("核心实现", "✅ 完成")

    # 缓存状态
    table.add_row("", "")
    table.add_row("[bold]缓存状态[/bold]", "")
    table.add_row("原始文章", "✓ 已缓存" if cache_info["articles"] else "- 无")
    table.add_row("清洗结果", "✓ 已缓存" if cache_info["cleaned"] else "- 无")
    table.add_row("主题分类", "✓ 已缓存" if cache_info["topics"] else "- 无")
    table.add_row("批次结果", f"{cache_info['batch_count']} 个")
    table.add_row("最终文档", f"{cache_info['final_count']} 个")

    console.print()
    console.print(table)
    console.print()

    console.print()

    console.print("[cyan]可用命令:[/cyan]")
    console.print("  python distill.py list-sources       # 查看内容源状态")
    console.print("  python distill.py fetch              # 抓取内容")
    console.print("  python distill.py run                # 运行蒸馏")
    console.print()


if __name__ == "__main__":
    cli()


@cli.command()
@click.option('--host', default='127.0.0.1', help='监听地址')
@click.option('--port', default=8000, type=int, help='监听端口')
def serve(host: str, port: int):
    """启动 Web UI 服务"""
    console.print(f"\n[bold cyan]启动 Web UI 服务...[/bold cyan]")
    console.print(f"[dim]地址: http://{host}:{port}[/dim]\n")
    
    import subprocess
    subprocess.run(["python", "web_ui.py"], check=True)
