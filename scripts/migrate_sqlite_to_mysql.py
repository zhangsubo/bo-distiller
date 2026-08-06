#!/usr/bin/env python3
"""
SQLite 到 MySQL 数据迁移工具

用法：
    python scripts/migrate_sqlite_to_mysql.py

环境变量（或在 .env 中配置）：
    MYSQL_HOST=127.0.0.1
    MYSQL_PORT=3306
    MYSQL_USER=root
    MYSQL_PASSWORD=root
    MYSQL_DATABASE=distill
    SQLITE_DB_PATH=./data/distiller.db
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from dotenv import load_dotenv

console = Console()

# 加载环境变量
load_dotenv()


def migrate():
    """执行迁移"""
    from src.storage import SQLiteStorage, reset_storage
    from src.mysql_storage import MySQLStorage

    # SQLite 配置
    sqlite_path = Path(os.getenv("SQLITE_DB_PATH", "./data/distiller.db"))
    if not sqlite_path.exists():
        console.print(f"[red]错误: SQLite 数据库文件不存在: {sqlite_path}[/red]")
        return False

    # MySQL 配置
    mysql_config = {
        "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
        "port": int(os.getenv("MYSQL_PORT", 3306)),
        "user": os.getenv("MYSQL_USER", "root"),
        "password": os.getenv("MYSQL_PASSWORD", "root"),
        "database": os.getenv("MYSQL_DATABASE", "distill"),
    }

    console.print("[bold cyan]Bo-Distiller 数据迁移工具[/bold cyan]")
    console.print(f"源数据库: SQLite - {sqlite_path}")
    console.print(f"目标数据库: MySQL - {mysql_config['host']}:{mysql_config['port']}/{mysql_config['database']}\n")

    # 初始化存储
    try:
        console.print("[dim]正在连接数据库...[/dim]")
        sqlite_storage = SQLiteStorage(sqlite_path)
        mysql_storage = MySQLStorage(**mysql_config)
        console.print("[green]✓ 数据库连接成功[/green]\n")
    except Exception as e:
        console.print(f"[red]✗ 数据库连接失败: {e}[/red]")
        return False

    # 获取 SQLite 统计信息
    stats = sqlite_storage.get_stats()
    total_articles = stats['total_articles']

    console.print(f"[bold]数据统计:[/bold]")
    console.print(f"  文章总数: {total_articles}")
    console.print(f"  来源数量: {len(stats['sources'])}")
    for source in stats['sources']:
        console.print(f"    - {source['source_type']}/{source['source_name']}: {source['count']} 篇")
    console.print()

    if total_articles == 0:
        console.print("[yellow]没有数据需要迁移[/yellow]")
        return True

    # 确认迁移
    confirm = console.input("[bold yellow]确认开始迁移？(y/N): [/bold yellow]")
    if confirm.lower() != 'y':
        console.print("[dim]迁移已取消[/dim]")
        return False

    console.print()

    # 开始迁移
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console
    ) as progress:

        # 1. 迁移文章
        task1 = progress.add_task("[cyan]迁移文章数据...", total=total_articles)
        batch_size = 100
        offset = 0
        migrated_articles = 0

        while offset < total_articles:
            articles = sqlite_storage.get_all_articles(limit=batch_size, offset=offset)
            if not articles:
                break

            saved = mysql_storage.save_articles(articles)
            migrated_articles += saved
            offset += batch_size
            progress.update(task1, completed=min(offset, total_articles))

        console.print(f"[green]✓ 文章迁移完成: {migrated_articles}/{total_articles}[/green]")

        # 2. 迁移主题
        task2 = progress.add_task("[cyan]迁移主题数据...", total=1)
        topics = sqlite_storage.get_topics()
        for name, keywords in topics.items():
            mysql_storage.set_topic(name, keywords)
        progress.update(task2, completed=1)
        console.print(f"[green]✓ 主题迁移完成: {len(topics)} 个[/green]")

        # 3. 迁移知识文档
        task3 = progress.add_task("[cyan]迁移知识文档...", total=1)
        knowledge_docs = sqlite_storage.get_knowledge_docs()
        for doc in knowledge_docs:
            mysql_storage.save_knowledge_doc(
                topic=doc['topic'],
                content=doc['content'],
                article_count=doc['article_count'],
                batch_count=doc['batch_count'],
                metadata=doc.get('metadata')
            )
        progress.update(task3, completed=1)
        console.print(f"[green]✓ 知识文档迁移完成: {len(knowledge_docs)} 个[/green]")

        # 4. 迁移设置
        task4 = progress.add_task("[cyan]迁移设置数据...", total=1)
        settings = sqlite_storage.get_all_settings()
        for key, value in settings.items():
            mysql_storage.set_setting(key, value)
        progress.update(task4, completed=1)
        console.print(f"[green]✓ 设置迁移完成: {len(settings)} 项[/green]")

    console.print()
    console.print("[bold green]🎉 数据迁移完成！[/bold green]")

    # 验证迁移结果
    mysql_stats = mysql_storage.get_stats()
    console.print(f"\n[bold]迁移后统计:[/bold]")
    console.print(f"  MySQL 文章总数: {mysql_stats['total_articles']}")

    if mysql_stats['total_articles'] == total_articles:
        console.print("[green]✓ 数据完整性验证通过[/green]")
    else:
        console.print(f"[yellow]⚠ 数据数量不匹配: SQLite({total_articles}) vs MySQL({mysql_stats['total_articles']})[/yellow]")

    return True


if __name__ == "__main__":
    try:
        success = migrate()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        console.print("\n[yellow]迁移已中断[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]迁移失败: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)
