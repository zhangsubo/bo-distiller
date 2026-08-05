#!/usr/bin/env python3
"""分批补抓 Cubox 文章完整正文，支持断点续传

每批 50 篇，间隔 1 分钟。进度写入 .cache/backfill_checkpoint.json，
重启后自动从上次位置继续。
"""

import json
import sys
import time
from pathlib import Path

from src.adapters.cubox_adapter import CuboxAdapter
from src.models import Article, SourceConfig

BATCH_SIZE = 50
REST_SECONDS = 60
CHECKPOINT_FILE = Path(".cache/backfill_checkpoint.json")


def load_checkpoint() -> dict:
    if CHECKPOINT_FILE.exists():
        return json.loads(CHECKPOINT_FILE.read_text())
    return {"done_ids": [], "skip_ids": []}


def save_checkpoint(ckpt: dict):
    CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
    CHECKPOINT_FILE.write_text(json.dumps(ckpt, ensure_ascii=False))


def main():
    print("初始化...", flush=True)
    adapter = CuboxAdapter(use_sqlite=True)
    source_config = SourceConfig(
        type="cubox", name="Cubox 收藏", identifier="cubox-cli", enabled=True
    )

    # 加载断点
    ckpt = load_checkpoint()
    done_ids = set(ckpt.get("done_ids", []))
    skip_ids = set(ckpt.get("skip_ids", []))

    # 获取所有需要补抓的文章（未完成且未标记跳过）
    all_articles = adapter._storage.get_articles_by_source("cubox", source_config.name)
    need_backfill = [
        a for a in all_articles
        if a.id not in done_ids
        and a.id not in skip_ids
        and not (a.metadata or {}).get("has_full_content")
    ]

    total = len(need_backfill)
    already_done = len(done_ids)
    print(f"已完成 {already_done} 篇，剩余 {total} 篇", flush=True)
    print(f"每批 {BATCH_SIZE} 篇，间隔 {REST_SECONDS}s，预计 {total // BATCH_SIZE} 批", flush=True)

    if total == 0:
        print("无需补抓，退出", flush=True)
        return

    batch_num = 0
    processed = 0

    for i in range(0, total, BATCH_SIZE):
        batch = need_backfill[i : i + BATCH_SIZE]
        batch_num += 1
        offset = already_done + i
        print(f"\n--- 第 {batch_num} 批 ({offset+1}-{offset+len(batch)}/{already_done+total}) ---", flush=True)

        for article in batch:
            cubox_id = (article.metadata or {}).get("cubox_id", article.id)
            sys.stdout.write(f"  {article.title[:45]}... ")
            sys.stdout.flush()

            detail = adapter.fetch_card_detail(cubox_id)
            if not detail:
                print("SKIP", flush=True)
                skip_ids.add(article.id)
                ckpt["skip_ids"] = list(skip_ids)
                save_checkpoint(ckpt)
                continue

            meta = article.metadata or {}
            meta["has_full_content"] = True
            meta["description"] = meta.get("description") or article.content[:200]

            if detail.get("annotations"):
                meta["annotations"] = detail["annotations"]
            if detail.get("insight"):
                meta["insight"] = {
                    "summary": detail["insight"].get("summary", ""),
                    "qas": detail["insight"].get("qas", []),
                }
            if detail.get("tags"):
                meta["tags"] = detail["tags"]

            updated = Article(
                id=article.id,
                title=article.title,
                content=detail.get("content") or article.content,
                url=article.url,
                source=article.source,
                author=detail.get("author") or article.author,
                published_date=article.published_date,
                fetched_date=article.fetched_date,
                metadata=meta,
            )
            adapter._storage.save_article(updated)
            done_ids.add(article.id)
            processed += 1
            print(f"OK ({len(detail.get('content',''))}c)", flush=True)

            # 每篇都保存断点
            ckpt["done_ids"] = list(done_ids)
            save_checkpoint(ckpt)

        if i + BATCH_SIZE < total:
            print(f"休息 {REST_SECONDS}s ...", flush=True)
            time.sleep(REST_SECONDS)

    print(f"\n完成！本次补抓 {processed} 篇，累计 {len(done_ids)} 篇", flush=True)


if __name__ == "__main__":
    main()
