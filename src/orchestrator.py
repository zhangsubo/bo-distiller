from pathlib import Path
from typing import Optional

from rich.console import Console

from .adapters.aggregator import ContentAggregator
from .cache import CacheManager
from .config import ConfigManager
from .llm_client import get_llm_client
from .processors.cleaner import ContentCleaner
from .processors.classifier import TopicClassifier
from .synthesizer import KnowledgeSynthesizer


def run_distillation(
    config_manager: ConfigManager,
    cache: CacheManager,
    model: str,
    incremental: bool = True,
    limit: Optional[int] = None,
    console: Optional[Console] = None,
) -> None:
    console = console or Console()
    config = config_manager.load_config()

    articles = cache.load_articles() if incremental else None
    if not articles:
        aggregator = ContentAggregator(config_manager)
        articles = aggregator.fetch_all(incremental=incremental)
        if not articles:
            console.print("[red]>> 未获取到任何文章，请检查内容源配置[/red]")
            return
        cache.save_articles(articles)

    if limit:
        console.print(f"[yellow]>> 测试模式：仅处理前 {limit} 篇文章[/yellow]\n")
        articles = articles[:limit]

    console.print("[bold]步骤 2/4: 清洗文章内容[/bold]")
    cleaned = cache.load_cleaned() if incremental else None
    if not cleaned:
        cleaner = ContentCleaner()
        cleaned = cleaner.clean_batch(articles)
        cache.save_cleaned(cleaned)

    console.print("[bold]步骤 3/4: 主题分类[/bold]")
    topics = cache.load_topics() if incremental else None
    if not topics:
        classifier = TopicClassifier(config_manager)
        topics = classifier.classify_batch(cleaned)
        cache.save_topics(topics)

    console.print(f"[bold]步骤 4/4: AI 知识合成（使用 {model}）[/bold]")
    llm = get_llm_client(provider=model, config_manager=config_manager)
    synthesizer = KnowledgeSynthesizer(
        llm_client=llm,
        cache_manager=cache,
        config_manager=config_manager,
    )
    results = synthesizer.distill_all(topics)

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
