#!/usr/bin/env python3
"""测试 MySQL 存储功能"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 直接测试 MySQL 连接，不导入其他模块
import pymysql
from rich.console import Console

console = Console()

def test_mysql():
    console.print("[bold cyan]测试 MySQL 连接和表结构[/bold cyan]\n")

    try:
        # 测试连接
        conn = pymysql.connect(
            host="127.0.0.1",
            port=3306,
            user="root",
            password="root",
            database="distill",
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor
        )
        console.print("[green]✓ MySQL 连接成功[/green]")

        with conn.cursor() as cursor:
            # 检查表
            cursor.execute("SHOW TABLES")
            tables = [row[list(row.keys())[0]] for row in cursor.fetchall()]
            console.print(f"[green]✓ 找到 {len(tables)} 个表[/green]")
            for table in tables:
                console.print(f"  - {table}")

            # 检查 articles 表结构
            console.print("\n[bold]articles 表结构:[/bold]")
            cursor.execute("DESCRIBE articles")
            for row in cursor.fetchall():
                console.print(f"  {row['Field']}: {row['Type']}")

            # 测试插入和查询
            cursor.execute("""
                INSERT INTO articles (id, title, content, source_type, source_name, fetched_date)
                VALUES (%s, %s, %s, %s, %s, NOW())
                ON DUPLICATE KEY UPDATE title=VALUES(title)
            """, ("test_001", "测试文章", "测试内容", "bookmark", "测试来源"))
            conn.commit()
            console.print("\n[green]✓ 数据插入成功[/green]")

            # 查询
            cursor.execute("SELECT COUNT(*) as count FROM articles")
            count = cursor.fetchone()['count']
            console.print(f"[green]✓ 当前文章数: {count}[/green]")

            # 清理测试数据
            cursor.execute("DELETE FROM articles WHERE id = %s", ("test_001",))
            conn.commit()
            console.print("[dim]测试数据已清理[/dim]")

        conn.close()
        console.print("\n[bold green]✓ 所有测试通过！[/bold green]")
        return True

    except pymysql.Error as e:
        console.print(f"[red]✗ MySQL 错误: {e}[/red]")
        return False

if __name__ == "__main__":
    try:
        success = test_mysql()
        sys.exit(0 if success else 1)
    except Exception as e:
        console.print(f"\n[red]测试失败: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)
