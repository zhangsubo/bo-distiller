#!/usr/bin/env python
"""
Cubox 内容智能分析工具
分析 SQLite 数据库中的文章，识别主题和聚类
"""

import sqlite3
import json
import re
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Any, Tuple
from urllib.parse import urlparse

DB_PATH = "data/distiller.db"


def load_articles_from_db(limit: int = None) -> List[Dict[str, Any]]:
    """从数据库加载文章"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = "SELECT * FROM articles ORDER BY fetched_date DESC"
    if limit:
        query += f" LIMIT {limit}"

    cursor.execute(query)
    articles = [dict(row) for row in cursor.fetchall()]

    conn.close()
    return articles


def extract_domain(url: str) -> str:
    """提取域名"""
    if not url:
        return "未知"
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path
        domain = re.sub(r'^www\.', '', domain)
        return domain
    except:
        return "未知"


def extract_keywords_chinese(text: str, top_n: int = 10) -> List[Tuple[str, int]]:
    """提取中文关键词（基于词频）"""
    # 移除特殊字符，保留中英文和数字
    text = re.sub(r'[^\w\s一-鿿]', ' ', text.lower())

    # 简单分词：提取2-4字的中文词，以及英文单词
    chinese_words = re.findall(r'[一-鿿]{2,4}', text)
    english_words = re.findall(r'\b[a-z]{3,}\b', text)

    all_words = chinese_words + english_words

    # 停用词
    stopwords = {
        '的', '了', '在', '是', '和', '有', '我', '不', '你', '他', '她', '它', '这个', '那个',
        '可以', '就是', '但是', '如果', '因为', '所以', '一个', '什么', '怎么', '为什么',
        'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of', 'and', 'or', 'but', 'with'
    }

    words = [w for w in all_words if w not in stopwords]

    counter = Counter(words)
    return counter.most_common(top_n)


def find_duplicate_topics(articles: List[Dict[str, Any]], min_articles: int = 2) -> Dict[str, List[Dict]]:
    """识别可能重复的主题（基于关键词相似度）"""

    # 为每篇文章提取关键词
    article_keywords = {}
    for article in articles:
        text = f"{article['title']} {(article.get('content') or '')[:500]}"
        keywords = extract_keywords_chinese(text, 10)
        article_keywords[article['id']] = set([kw for kw, _ in keywords])

    # 按关键词分组
    keyword_groups = defaultdict(list)
    for article in articles:
        title = article['title']
        keywords = extract_keywords_chinese(title, 5)

        for kw, _ in keywords:
            if len(kw) >= 2:  # 至少2个字符
                keyword_groups[kw].append(article)

    # 筛选有多篇文章的关键词
    duplicate_topics = {
        kw: arts for kw, arts in keyword_groups.items()
        if len(arts) >= min_articles
    }

    # 按文章数排序
    sorted_topics = dict(
        sorted(duplicate_topics.items(), key=lambda x: len(x[1]), reverse=True)
    )

    return sorted_topics


def analyze_by_domain(articles: List[Dict[str, Any]]) -> Dict[str, int]:
    """按来源网站分析"""
    domains = [extract_domain(a.get('url', '')) for a in articles]
    return dict(Counter(domains).most_common(20))


def analyze_by_time(articles: List[Dict[str, Any]]) -> Dict[str, int]:
    """按时间分析"""
    dates = []
    for a in articles:
        date = a.get('fetched_date', '')
        if date:
            dates.append(date[:7])  # YYYY-MM

    return dict(sorted(Counter(dates).items(), reverse=True)[:12])


def detect_similar_articles(articles: List[Dict[str, Any]], threshold: float = 0.5) -> List[List[Dict]]:
    """检测相似文章（简单版本：基于标题相似度）"""

    similar_groups = []
    processed = set()

    for i, article1 in enumerate(articles):
        if article1['id'] in processed:
            continue

        group = [article1]
        title1_words = set(extract_keywords_chinese(article1['title'], 20))

        for j, article2 in enumerate(articles[i+1:], i+1):
            if article2['id'] in processed:
                continue

            title2_words = set(extract_keywords_chinese(article2['title'], 20))

            # 计算 Jaccard 相似度
            if title1_words and title2_words:
                intersection = len(title1_words & title2_words)
                union = len(title1_words | title2_words)
                similarity = intersection / union if union > 0 else 0

                if similarity >= threshold:
                    group.append(article2)
                    processed.add(article2['id'])

        if len(group) >= 2:
            similar_groups.append(group)
            processed.add(article1['id'])

    return similar_groups


def generate_analysis_report(articles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """生成完整分析报告"""

    print(f"\n{'='*70}")
    print(f"📊 Cubox 内容分析报告")
    print(f"{'='*70}\n")

    print(f"文章总数: {len(articles)}")
    print(f"数据来源: {DB_PATH}")
    print()

    # 1. 来源类型统计
    print(f"\n{'─'*70}")
    print("📁 来源类型统计")
    print(f"{'─'*70}")
    source_types = Counter(a.get('source_type', '未知') for a in articles)
    for source_type, count in source_types.most_common():
        print(f"   {source_type}: {count} 篇")

    # 2. 高频关键词
    print(f"\n{'─'*70}")
    print("🔤 标题高频关键词 TOP 30")
    print(f"{'─'*70}")
    all_titles = " ".join(a['title'] for a in articles)
    top_keywords = extract_keywords_chinese(all_titles, 30)
    for i, (kw, count) in enumerate(top_keywords, 1):
        print(f"   {i:2d}. {kw:15s} ({count} 次)")

    # 3. 潜在主题聚类
    print(f"\n{'─'*70}")
    print("🎯 潜在主题聚类（相同关键词的文章）")
    print(f"{'─'*70}")
    duplicate_topics = find_duplicate_topics(articles, min_articles=3)

    for i, (keyword, arts) in enumerate(list(duplicate_topics.items())[:20], 1):
        print(f"\n   {i}. '{keyword}' ({len(arts)} 篇)")
        for j, article in enumerate(arts[:3], 1):
            title = article['title'][:65]
            print(f"      {j}. {title}")
        if len(arts) > 3:
            print(f"      ... 还有 {len(arts)-3} 篇")

    # 4. 来源网站统计
    print(f"\n{'─'*70}")
    print("🌐 来源网站 TOP 15")
    print(f"{'─'*70}")
    domains = analyze_by_domain(articles)
    for domain, count in list(domains.items())[:15]:
        print(f"   {domain:40s} {count:4d} 篇")

    # 5. 时间分布
    print(f"\n{'─'*70}")
    print("📅 收藏时间分布")
    print(f"{'─'*70}")
    time_dist = analyze_by_time(articles)
    for date, count in list(time_dist.items())[:12]:
        bar = '█' * (count // 10) + '▌' if count % 10 >= 5 else '█' * (count // 10)
        print(f"   {date}: {bar} ({count} 篇)")

    # 6. 相似文章检测
    print(f"\n{'─'*70}")
    print("🔍 相似文章检测（可能是同一主题的不同来源）")
    print(f"{'─'*70}")
    similar_groups = detect_similar_articles(articles, threshold=0.4)

    for i, group in enumerate(similar_groups[:10], 1):
        print(f"\n   相似组 {i} ({len(group)} 篇):")
        for j, article in enumerate(group, 1):
            print(f"      {j}. {article['title'][:65]}")
            print(f"         来源: {extract_domain(article.get('url', ''))}")

    if len(similar_groups) > 10:
        print(f"\n   ... 还有 {len(similar_groups)-10} 组相似文章")

    # 生成报告数据
    report = {
        'total_articles': len(articles),
        'source_types': dict(source_types),
        'top_keywords': [(kw, count) for kw, count in top_keywords],
        'potential_topics': {kw: len(arts) for kw, arts in list(duplicate_topics.items())[:50]},
        'top_domains': domains,
        'time_distribution': time_dist,
        'similar_groups_count': len(similar_groups),
    }

    # 保存报告
    report_file = Path("cubox_analysis_report.json")
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*70}")
    print(f"✅ 分析完成！详细报告已保存到: {report_file}")
    print(f"{'='*70}\n")

    return report


def main():
    import argparse

    parser = argparse.ArgumentParser(description='分析 Cubox 内容')
    parser.add_argument('--limit', type=int, help='限制分析的文章数量（用于快速测试）')
    parser.add_argument('--full', action='store_true', help='完整分析所有文章')

    args = parser.parse_args()

    print("🔍 正在从数据库加载文章...")
    articles = load_articles_from_db(limit=args.limit)

    if not articles:
        print("❌ 数据库中没有找到文章")
        return

    print(f"✓ 已加载 {len(articles)} 篇文章\n")

    # 生成分析报告
    report = generate_analysis_report(articles)

    print("\n💡 下一步建议:")
    print("   1. 查看 cubox_analysis_report.json 了解详细统计")
    print("   2. 根据高频关键词和潜在主题优化分类规则")
    print("   3. 运行 python classify_upgrade.py 使用升级的智能分类器")


if __name__ == "__main__":
    main()
