#!/usr/bin/env python3
"""
回灌脚本：把服务器下载完成的 wechat_articles/ 产物回灌进 distiller.db

语义与主项目 src/services/wechat_downloader.py 的 process_article 回写一致：
- articles 表 content 更新为全文，metadata 合并 wechat_files / wechat_downloaded_at
- wechat_downloads 表置 done（幂等），主项目内置队列不会重复下载

自包含，不 import src.*，仅用标准库 + 可选 beautifulsoup4。
"""

import argparse
import json
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# 微信文章 URL 特征（前缀撞车保护用）
WECHAT_URL_KEYWORD = "mp.weixin.qq.com"


def log(msg: str):
    """带时间戳的单行日志"""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def extract_id_prefix(dir_name: str):
    """从文章目录名提取尾部 _xxxxxxxx 的 8 位 id 前缀，取不到返回 None"""
    m = re.search(r"_([0-9a-zA-Z]{8})$", dir_name)
    return m.group(1) if m else None


def load_url_map(urls_file: Path) -> dict:
    """从 urls.jsonl 加载 id[:8] -> 完整 URL 的映射

    Returns:
        dict: {id_prefix_8chars: full_url}
    """
    url_map = {}
    if not urls_file.exists():
        return url_map
    with open(urls_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            if "id" in item and "url" in item:
                url_map[item["id"][:8]] = item["url"]
    return url_map


def read_content(article_dir: Path, min_len: int):
    """读取正文：优先 article.md，缺失则用 article.html 转纯文本

    Returns:
        (正文, files 字典) 或 (None, files 字典) 表示正文无效
    """
    files = {}
    md_path = article_dir / "article.md"
    html_path = article_dir / "article.html"

    content = None
    if md_path.exists():
        content = md_path.read_text(encoding="utf-8")
        files["markdown"] = str(md_path)
    if html_path.exists():
        files["html"] = str(html_path)
        if content is None:
            try:
                from bs4 import BeautifulSoup
                content = BeautifulSoup(
                    html_path.read_text(encoding="utf-8"), "html.parser"
                ).get_text("\n")
            except ImportError:
                log(f"  警告: {article_dir.name} 只有 HTML 但未安装 beautifulsoup4，跳过")
                return None, files

    if not content or len(content.strip()) < min_len:
        return None, files
    return content, files


def find_article_by_url(conn, url: str):
    """按 URL 精确匹配 articles 行（排除重复），返回 (row, 匹配数)

    优先返回 url_duplicate=0 的记录；若全部是重复的，返回 None。
    """
    rows = conn.execute(
        "SELECT id, url, content, metadata, url_duplicate FROM articles WHERE url = ?",
        (url,),
    ).fetchall()
    if not rows:
        return None, 0
    # 优先返回非重复记录
    non_dupes = [r for r in rows if r["url_duplicate"] != 1]
    if non_dupes:
        return non_dupes[0], len(rows)
    # 全部是重复的，返回 None
    return None, len(rows)


def import_one(db_path: Path, article_dir: Path, id_prefix: str,
               url_map: dict, min_len: int, dry_run: bool) -> str:
    """回灌单篇，返回结果类别：updated / skipped / unmatched / invalid / error

    每篇独立事务，出错回滚不影响其他文章。
    """
    content, files = read_content(article_dir, min_len)
    if content is None:
        return "invalid"

    # 从 url_map 获取完整 URL
    full_url = url_map.get(id_prefix)
    if not full_url:
        log(f"  警告: id 前缀 {id_prefix} 在 urls.jsonl 中未找到对应 URL，跳过")
        return "unmatched"

    # 只处理微信文章
    if WECHAT_URL_KEYWORD not in full_url:
        log(f"  警告: id 前缀 {id_prefix} 对应的不是微信文章 URL，跳过: {full_url[:60]}")
        return "unmatched"

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        row, match_count = find_article_by_url(conn, full_url)
        if row is None:
            if match_count > 0:
                log(f"  跳过: URL 的所有记录均为重复标记: {full_url[:80]}")
                return "skipped"
            log(f"  警告: URL 在 articles 表中未匹配: {full_url[:80]}")
            return "unmatched"

        article_id = row["id"]

        # 已是全文或无变化则跳过
        old_content = row["content"] or ""
        if old_content.strip() == content.strip() or len(old_content) >= len(content):
            return "skipped"

        # 合并 metadata（与主项目同格式）
        metadata = json.loads(row["metadata"]) if row["metadata"] else {}
        metadata["wechat_files"] = files
        metadata["wechat_downloaded_at"] = datetime.now().isoformat()

        if dry_run:
            log(f"  [dry-run] 将更新 {article_id}：content {len(old_content)} -> {len(content)} 字符")
            return "updated"

        with conn:  # 单篇事务，出错自动回滚
            conn.execute("""
                UPDATE articles SET content = ?, metadata = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (content, json.dumps(metadata, ensure_ascii=False), article_id))

            # wechat_downloads 置 done（已有 done 行则不动，幂等）
            existing = conn.execute(
                "SELECT status FROM wechat_downloads WHERE article_id = ?",
                (article_id,),
            ).fetchone()
            if not existing:
                conn.execute("""
                    INSERT INTO wechat_downloads (article_id, url, status, files)
                    VALUES (?, ?, 'done', ?)
                """, (article_id, full_url, json.dumps(files, ensure_ascii=False)))
            elif existing["status"] != "done":
                conn.execute("""
                    UPDATE wechat_downloads SET status = 'done', files = ?, last_error = NULL,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE article_id = ?
                """, (json.dumps(files, ensure_ascii=False), article_id))

        log(f"  已更新 {article_id}：content {len(old_content)} -> {len(content)} 字符")
        return "updated"
    except Exception as e:
        log(f"  错误: {article_dir.name} 回灌失败: {e}")
        return "error"
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="把 wechat_articles 产物回灌进 distiller.db")
    parser.add_argument("--articles-dir", default="./wechat_articles", help="下载产物根目录")
    parser.add_argument("--db", default="../data/distiller.db", help="distiller.db 路径")
    parser.add_argument("--urls", help="urls.jsonl 路径（默认自动查找）")
    parser.add_argument("--dry-run", action="store_true", help="只打印将做什么，不写库")
    parser.add_argument("--min-content-len", type=int, default=200,
                        help="正文短于此值认为无效跳过（默认 200）")
    args = parser.parse_args()

    articles_dir = Path(args.articles_dir)
    db_path = Path(args.db)
    if not articles_dir.exists():
        raise SystemExit(f"产物目录不存在: {articles_dir}")
    if not db_path.exists():
        raise SystemExit(f"数据库不存在: {db_path}")

    # 加载 urls.jsonl 构建 id[:8] -> URL 映射
    if args.urls:
        urls_file = Path(args.urls)
    else:
        # 自动查找：先尝试 articles-dir 的父目录/wechat-exporter/，再尝试脚本同目录
        urls_file = Path(args.articles_dir).parent / "wechat-exporter" / "urls.jsonl"
        if not urls_file.exists():
            urls_file = Path(__file__).parent / "urls.jsonl"
    url_map = load_url_map(urls_file)
    log(f"从 {urls_file} 加载了 {len(url_map)} 条 URL 映射")

    # 递归扫描 月份目录/文章目录/article.md|html
    article_dirs = sorted(
        d for d in articles_dir.glob("*/*/")
        if (d / "article.md").exists() or (d / "article.html").exists()
    )
    log(f"扫描到 {len(article_dirs)} 个文章目录（dry_run={args.dry_run}）")

    stats = {"updated": 0, "skipped": 0, "unmatched": 0, "invalid": 0, "error": 0}
    unmatched = []

    for article_dir in article_dirs:
        id_prefix = extract_id_prefix(article_dir.name)
        if not id_prefix:
            log(f"  警告: 目录名无 id 前缀，跳过: {article_dir.name}")
            stats["unmatched"] += 1
            unmatched.append(("(无前缀)", article_dir.name))
            continue

        result = import_one(db_path, article_dir, id_prefix, url_map,
                            args.min_content_len, args.dry_run)
        stats[result] += 1
        if result == "unmatched":
            unmatched.append((id_prefix, article_dir.name))

    log(f"完成：scanned {len(article_dirs)} / updated {stats['updated']} / "
        f"skipped {stats['skipped']} / invalid {stats['invalid']} / "
        f"unmatched {stats['unmatched']} / errors {stats['error']}")
    if unmatched:
        log("未匹配列表：")
        for prefix, name in unmatched:
            print(f"  {prefix}  {name}", flush=True)


if __name__ == "__main__":
    main()
