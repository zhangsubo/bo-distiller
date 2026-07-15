#!/usr/bin/env python
"""
Cubox 内容分析工具
分析已收藏的文章，识别主题和重复内容
"""

import pickle
import json
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Any
import re
import sys

def load_cached_data():
    """加载缓存的数据（直接读取不导入项目模块）"""
    cache_dir = Path(".cache")

    data = {}

    # 加载文章
    articles_file = cache_dir / "articles.pkl"
    if articles_file.exists():
        try:
            # 尝试直接加载，如果是 pydantic 对象则转为字典
            with open(articles_file, 'rb') as f:
                raw_articles = pickle.load(f)

            # 转换为字典列表
            articles = []
            for article in raw_articles:
                if hasattr(article, 'dict'):
                    # Pydantic v1
                    articles.append(article.dict())
                elif hasattr(article, 'model_dump'):
                    # Pydantic v2
                    articles.append(article.model_dump())
                elif isinstance(article, dict):
                    articles.append(article)
                else:
                    # 尝试访问属性
                    articles.append({
                        'id': getattr(article, 'id', ''),
                        'title': getattr(article, 'title', ''),
                        'content': getattr(article, 'content', ''),
                        'url': getattr(article, 'url', None),
                        'source': getattr(article, 'source', {}).__dict__ if hasattr(getattr(article, 'source', {}), '__dict__') else {},
                        'author': getattr(article, 'author', None),
                        'published_date': getattr(article, 'published_date', None),
                        'fetched_date': getattr(article, 'fetched_date', None),
                        'metadata': getattr(article, 'metadata', {}),
                    })

            data['articles'] = articles
        except Exception as e:
            print(f"⚠️  加载文章数据失败: {e}")
            return data

    # 加载分类结果
    topics_file = cache_dir / "topics.pkl"
    if topics_file.exists():
        try:
            with open(topics_file, 'rb') as f:
                raw_topics = pickle.load(f)

            # 转换为字典
            topics = {}
            for topic_name, topic_articles in raw_topics.items():
                converted_articles = []
                for article in topic_articles:
                    if hasattr(article, 'dict'):
                        converted_articles.append(article.dict())
                    elif hasattr(article, 'model_dump'):
                        converted_articles.append(article.model_dump())
                    elif isinstance(article, dict):
                        converted_articles.append(article)
                    else:
                        converted_articles.append({
                            'id': getattr(article, 'id', ''),
                            'title': getattr(article, 'title', ''),
                            'content': getattr(article, 'content', ''),
                            'url': getattr(article, 'url', None),
                        })
                topics[topic_name] = converted_articles

            data['topics'] = topics
        except Exception as e:
            print(f"⚠️  加载分类数据失败: {e}")

    return data

def extract_keywords(text: str, top_n: int = 10) -> List[str]:
    """提取关键词（简单版本）"""
    # 移除标点和特殊字符
    text = re.sub(r'[^\w\s一-鿿]', ' ', text.lower())

    # 分词（简单按空格分）
    words = text.split()

    # 过滤常见词和短词
    stopwords = {'的', '了', '在', '是', '和', '有', '我', '不', '你', '他', '她', '它',
                 'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of', 'and', 'or'}

    words = [w for w in words if len(w) > 1 and w not in stopwords]

    # 统计频率
    counter = Counter(words)
    return [word for word, _ in counter.most_common(top_n)]

def analyze_articles(articles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """分析文章集合"""

    print(f"\n{'='*60}")
    print(f"文章总数: {len(articles)}")
    print(f"{'='*60}\n")

    # 1. 来源统计
    sources = Counter(a.get('source', {}).get('type', '未知') for a in articles)
    print("📊 来源统计:")
    for source, count in sources.most_common():
        print(f"   {source}: {count} 篇")

    # 2. 标题关键词分析
    print("\n🔤 标题高频词:")
    all_titles = " ".join(a.get('title', '') for a in articles)
    title_keywords = extract_keywords(all_titles, 20)
    for i, kw in enumerate(title_keywords[:10], 1):
        print(f"   {i}. {kw}")

    # 3. 识别可能的重复主题
    print("\n🔍 潜在主题聚类（基于标题关键词）:")

    # 按关键词分组文章
    keyword_groups = defaultdict(list)
    for article in articles:
        title = article.get('title', '')
        keywords = extract_keywords(title, 5)
        for kw in keywords:
            if len(kw) > 2:  # 只考虑3字符以上的词
                keyword_groups[kw].append(article)

    # 显示有多篇文章的关键词
    multi_article_keywords = {k: v for k, v in keyword_groups.items() if len(v) >= 2}

    sorted_keywords = sorted(multi_article_keywords.items(), key=lambda x: len(x[1]), reverse=True)

    for kw, arts in sorted_keywords[:15]:
        print(f"\n   '{kw}' ({len(arts)} 篇):")
        for a in arts[:3]:
            print(f"      - {a.get('title', '无标题')[:60]}")
        if len(arts) > 3:
            print(f"      ... 还有 {len(arts)-3} 篇")

    # 4. URL 域名统计
    print("\n\n🌐 来源网站 TOP 10:")
    urls = [a.get('url', '') for a in articles if a.get('url')]
    domains = []
    for url in urls:
        match = re.search(r'https?://([^/]+)', url)
        if match:
            domain = match.group(1)
            # 移除 www.
            domain = re.sub(r'^www\.', '', domain)
            domains.append(domain)

    domain_counter = Counter(domains)
    for domain, count in domain_counter.most_common(10):
        print(f"   {domain}: {count} 篇")

    # 5. 日期分布
    print("\n\n📅 时间分布:")
    dates = []
    for a in articles:
        date = a.get('fetched_date') or a.get('published_date')
        if date:
            if isinstance(date, str):
                dates.append(date[:7])  # YYYY-MM
            else:
                dates.append(str(date)[:7])

    date_counter = Counter(dates)
    for date, count in sorted(date_counter.items(), reverse=True)[:6]:
        print(f"   {date}: {count} 篇")

    return {
        'total': len(articles),
        'sources': dict(sources),
        'top_keywords': title_keywords[:20],
        'potential_clusters': {k: len(v) for k, v in sorted_keywords[:20]},
        'top_domains': dict(domain_counter.most_common(10)),
    }

def analyze_topics(topics: Dict[str, List[Dict[str, Any]]]) -> None:
    """分析现有分类结果"""

    print(f"\n\n{'='*60}")
    print(f"现有分类结果")
    print(f"{'='*60}\n")

    print(f"分类数量: {len(topics)}")
    print()

    for topic_name, articles in topics.items():
        print(f"【{topic_name}】 {len(articles)} 篇")

        # 显示该分类下的文章标题（前5篇）
        for i, article in enumerate(articles[:5], 1):
            title = article.get('title', '无标题')
            print(f"   {i}. {title[:70]}")

        if len(articles) > 5:
            print(f"   ... 还有 {len(articles)-5} 篇")

        print()

def generate_report(data: Dict[str, Any], output_file: str = "content_analysis_report.json"):
    """生成分析报告"""

    articles = data.get('articles', [])
    topics = data.get('topics', {})

    # 分析文章
    article_analysis = analyze_articles(articles)

    # 分析现有分类
    if topics:
        analyze_topics(topics)

    # 保存报告
    report = {
        'summary': article_analysis,
        'current_classification': {
            topic: len(arts) for topic, arts in topics.items()
        } if topics else {},
        'timestamp': str(Path('.cache/articles.pkl').stat().st_mtime if Path('.cache/articles.pkl').exists() else 0)
    }

    output_path = Path(output_file)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n\n✅ 分析报告已保存到: {output_path}")

    return report

def main():
    print("🔍 开始分析 Cubox 内容...")

    # 加载数据
    data = load_cached_data()

    if not data.get('articles'):
        print("❌ 未找到缓存的文章数据，请先运行 distill.py 抓取内容")
        return

    # 生成报告
    report = generate_report(data)

    print("\n" + "="*60)
    print("💡 建议:")
    print("="*60)
    print("1. 查看 content_analysis_report.json 了解详细统计")
    print("2. 根据高频关键词优化分类规则")
    print("3. 使用 python classify_upgrade.py 运行升级的分类器")

if __name__ == "__main__":
    main()
