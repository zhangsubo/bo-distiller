#!/usr/bin/env python3
"""
从 SQLite 导出主题和提示词配置到 MySQL
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.storage import SQLiteStorage
from src.mysql_storage import MySQLStorage
from rich.console import Console

console = Console()

def migrate_settings():
    """迁移主题和提示词配置"""
    # 初始化存储
    sqlite_storage = SQLiteStorage(Path("./data/distiller.db"))
    mysql_storage = MySQLStorage(
        host="127.0.0.1",
        port=3306,
        user="root",
        password="root",
        database="distill"
    )

    # 要迁移的配置项
    settings_to_migrate = ['topics', 'prompts']

    console.print("[bold cyan]开始迁移配置...[/bold cyan]\n")

    for key in settings_to_migrate:
        console.print(f"[blue]→[/blue] 迁移 {key}...")

        # 从 SQLite 读取
        value = sqlite_storage.get_setting(key)

        if value is None:
            console.print(f"[yellow]  ⚠ {key} 在 SQLite 中不存在，跳过[/yellow]")
            continue

        # 检查数据类型和大小
        import json
        if isinstance(value, dict):
            json_str = json.dumps(value, ensure_ascii=False)
            size_kb = len(json_str) / 1024
            console.print(f"[dim]  数据大小: {size_kb:.2f} KB[/dim]")

        # 写入 MySQL
        try:
            mysql_storage.set_setting(key, value)
            console.print(f"[green]  ✓ {key} 迁移成功[/green]")
        except Exception as e:
            console.print(f"[red]  ✗ {key} 迁移失败: {e}[/red]")

    console.print("\n[bold green]✓ 配置迁移完成！[/bold green]")

    # 验证迁移结果
    console.print("\n[bold]验证迁移结果:[/bold]")
    for key in settings_to_migrate:
        sqlite_value = sqlite_storage.get_setting(key)
        mysql_value = mysql_storage.get_setting(key)

        if sqlite_value and mysql_value:
            console.print(f"  {key}: [green]✓ 两边都存在[/green]")
        elif mysql_value:
            console.print(f"  {key}: [green]✓ MySQL 已有数据[/green]")
        else:
            console.print(f"  {key}: [yellow]⚠ MySQL 中缺失[/yellow]")

if __name__ == "__main__":
    try:
        migrate_settings()
    except Exception as e:
        console.print(f"\n[red]迁移失败: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)
