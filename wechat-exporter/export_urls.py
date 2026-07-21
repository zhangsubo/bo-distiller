#!/usr/bin/env python3
"""
从 bo-distiller 的 distiller.db 导出微信文章 URL 清单（JSONL）

每行格式：{"id": ..., "title": ..., "url": ..., "published_date": ...}
按 url 去重；可选跳过已下载的文章（--skip-done）。
"""

import argparse
import json
import sqlite3
from pathlib import Path


def load_done_ids(download_dir: Path) -> set:
    """扫描下载目录，收集已有 article.md/article.html 的文章 id 前缀

    目录命名格式为 {YYYY-MM}/{safe_title}_{id[:8]}/，用 id 前缀匹配。
    """
    done = set()
    if not download_dir.exists():
        return done
    for article_dir in download_dir.glob("*/*/"):
        if (article_dir / "article.md").exists() or (article_dir / "article.html").exists():
            # 目录名最后一段下划线后为 id 前 8 位
            done.add(article_dir.name.rsplit("_", 1)[-1])
    return done


def main():
    parser = argparse.ArgumentParser(description="导出微信文章 URL 清单（JSONL）")
    parser.add_argument("--db", default="../data/distiller.db", help="distiller.db 路径")
    parser.add_argument("-o", default="urls.jsonl", help="输出 JSONL 文件路径")
    parser.add_argument("--skip-done", metavar="DOWNLOAD_DIR",
                        help="跳过该下载目录下已完成的文章")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        raise SystemExit(f"数据库不存在: {db_path}")

    done_prefixes = set()
    if args.skip_done:
        done_prefixes = load_done_ids(Path(args.skip_done))
        print(f"已下载目录中检测到 {len(done_prefixes)} 篇已完成文章，将跳过")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT id, title, url, published_date FROM articles
        WHERE url LIKE '%mp.weixin.qq.com%'
        ORDER BY published_date
    """).fetchall()
    conn.close()

    total = len(rows)
    seen_urls = set()
    exported = 0
    skipped_done = 0

    with open(args.o, "w", encoding="utf-8") as f:
        for row in rows:
            url = row["url"]
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            if done_prefixes and row["id"][:8] in done_prefixes:
                skipped_done += 1
                continue
            f.write(json.dumps({
                "id": row["id"],
                "title": row["title"],
                "url": url,
                "published_date": row["published_date"],
            }, ensure_ascii=False) + "\n")
            exported += 1

    print(f"查询总数: {total}")
    print(f"按 URL 去重后: {len(seen_urls)}")
    if args.skip_done:
        print(f"跳过已下载: {skipped_done}")
    print(f"导出: {exported} -> {args.o}")


if __name__ == "__main__":
    main()
