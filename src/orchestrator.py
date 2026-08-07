import threading
from pathlib import Path
from typing import Callable, Optional

from rich.console import Console

from .cache import CacheManager
from .config import ConfigManager
from .llm_client import get_llm_client
from .processors.cleaner import ContentCleaner
from .processors.classifier import TopicClassifier
from .storage import get_storage
from .synthesizer import KnowledgeSynthesizer


def run_distillation(
    config_manager: ConfigManager,
    cache: CacheManager,
    model: str,
    incremental: bool = True,
    limit: Optional[int] = None,
    console: Optional[Console] = None,
    cancel_event: Optional[threading.Event] = None,
) -> None:
    console = console or Console()
    config = config_manager.load_config()

    # 从 SQLite 数据库读取已同步的文章，而不是重新抓取
    console.print("[bold]步骤 1/4: 从数据库加载文章[/bold]")
    articles = cache.load_articles() if incremental else None
    if not articles:
        storage = get_storage()
        articles = storage.get_all_articles()
        if not articles:
            console.print("[red]>> 数据库中没有文章，请先同步内容源[/red]")
            console.print("[yellow]>> 提示：访问设置页面进行 Cubox 同步[/yellow]")
            return
        console.print(f"[green]>> 从数据库加载了 {len(articles)} 篇文章[/green]")
        cache.save_articles(articles)

    if limit:
        console.print(f"[yellow]>> 测试模式：仅处理前 {limit} 篇文章[/yellow]\n")
        articles = articles[:limit]

    console.print("[bold]步骤 2/4: 清洗文章内容[/bold]")
    # incremental=False 时跳过缓存，强制重新清洗
    cleaned = cache.load_cleaned(articles=articles) if incremental else None
    if not cleaned:
        cleaner = ContentCleaner()
        cleaned = cleaner.clean_batch(articles)
        cache.save_cleaned_with_fingerprint(cleaned, articles)

    console.print("[bold]步骤 3/4: 主题分类[/bold]")
    topics_config = config_manager.load_topics()
    # incremental=False 时跳过缓存，强制重新分类
    topics = cache.load_topics(cleaned=cleaned, topics_config=topics_config) if incremental else None
    if not topics:
        classifier = TopicClassifier(config_manager)
        topics = classifier.classify_batch(cleaned)
        cache.save_topics_with_fingerprint(topics, cleaned, topics_config)

    console.print(f"[bold]步骤 4/4: AI 知识合成（使用 {model}）[/bold]")
    llm = get_llm_client(provider=model, config_manager=config_manager)
    synthesizer = KnowledgeSynthesizer(
        llm_client=llm,
        cache_manager=cache,
        config_manager=config_manager,
        cancel_event=cancel_event,
    )
    results = synthesizer.distill_all(topics, incremental=incremental)

    console.print("[bold]生成最终文档[/bold]")
    output_dir = Path(config.output.local_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for topic, doc in results.items():
        output_file = output_dir / f"{topic}.md"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"# {topic}\n\n")
            f.write(f"> 从 {doc.article_count} 篇文章中提炼的知识体系\n\n")
            f.write("---\n\n")
            f.write(doc.content)
        console.print(f"[green]>> 生成文档: {output_file}[/green]")

    index_file = output_dir / "INDEX.md"
    with open(index_file, "w", encoding="utf-8") as f:
        f.write("# 知识库索引\n\n")
        f.write("> 由 Bo-Distiller 自动生成\n\n")
        f.write("## 主题列表\n\n")
        for topic, doc in results.items():
            f.write(f"- [{topic}]({topic}.md) - {doc.article_count} 篇文章\n")
    console.print(f"[green]>> 生成索引: {index_file}[/green]")

    console.print("\n[bold green]========================================[/bold green]")
    console.print("[bold green]>> 蒸馏完成！[/bold green]")
    console.print(f"[bold green]>> 输出目录: {output_dir}[/bold green]")
    console.print("[bold green]========================================[/bold green]\n")
