#!/usr/bin/env python
"""
智能分类升级工具
基于 LLM 的智能分类，自动识别主题并去重
"""

import sqlite3
import json
import re
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any
import os

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


def batch_articles_by_keyword(articles: List[Dict[str, Any]], top_n: int = 30) -> Dict[str, List[Dict]]:
    """按关键词初步分组"""
    from collections import Counter

    # 提取所有标题的关键词
    all_keywords = []
    for article in articles:
        title = article['title']
        # 提取中文词（2-4字）和英文词
        chinese_words = re.findall(r'[一-鿿]{2,4}', title)
        english_words = re.findall(r'\b[a-zA-Z]{3,}\b', title.lower())
        all_keywords.extend(chinese_words + english_words)

    # 统计高频关键词
    keyword_counter = Counter(all_keywords)
    top_keywords = [kw for kw, _ in keyword_counter.most_common(top_n)]

    # 按关键词分组
    keyword_groups = defaultdict(list)
    uncategorized = []

    for article in articles:
        title = article['title'].lower()
        matched = False

        for keyword in top_keywords:
            if keyword.lower() in title:
                keyword_groups[keyword].append(article)
                matched = True
                break  # 只匹配第一个关键词

        if not matched:
            uncategorized.append(article)

    # 只保留有多篇文章的分组
    result = {kw: arts for kw, arts in keyword_groups.items() if len(arts) >= 3}

    if uncategorized:
        result['其他'] = uncategorized

    return result


def classify_with_llm(articles: List[Dict[str, Any]], api_key: str = None) -> Dict[str, List[Dict]]:
    """使用 LLM 进行智能分类"""

    if not api_key:
        api_key = os.getenv('DEEPSEEK_API_KEY')

    if not api_key:
        print("⚠️  未配置 DEEPSEEK_API_KEY，跳过 LLM 分类")
        return {}

    try:
        from openai import OpenAI
    except ImportError:
        print("⚠️  未安装 openai 库，跳过 LLM 分类")
        return {}

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com"
    )

    # 准备文章标题列表
    titles = [f"{i+1}. {a['title']}" for i, a in enumerate(articles[:100])]  # 限制100篇避免token过多
    titles_text = "\n".join(titles)

    prompt = f"""请分析以下文章标题，将它们分类到合适的主题中。

要求：
1. 识别主要的主题领域（例如：AI工具、编程工具、开源项目、数据资产、教程指南等）
2. 每个主题用简洁的2-4个字命名
3. 返回 JSON 格式：{{"主题名": [文章序号列表]}}
4. 如果某些文章不属于任何主题，放入"其他"分类

文章标题：
{titles_text}

请直接返回 JSON，不要其他解释。"""

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一个内容分类专家，擅长识别文章主题。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
        )

        result_text = response.choices[0].message.content.strip()

        # 提取 JSON（去除可能的代码块标记）
        result_text = re.sub(r'^```json\s*', '', result_text)
        result_text = re.sub(r'\s*```$', '', result_text)

        classification = json.loads(result_text)

        # 转换序号为文章对象
        categorized = {}
        for topic, indices in classification.items():
            categorized[topic] = [articles[i-1] for i in indices if 0 < i <= len(articles)]

        return categorized

    except Exception as e:
        print(f"⚠️  LLM 分类失败: {e}")
        return {}


def merge_duplicate_articles(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """合并重复文章（基于标题相似度）"""

    unique_articles = []
    seen_titles = set()

    for article in articles:
        title = article['title'].strip().lower()

        # 简单去重：完全相同的标题
        if title not in seen_titles:
            unique_articles.append(article)
            seen_titles.add(title)

    removed_count = len(articles) - len(unique_articles)
    if removed_count > 0:
        print(f"   ✓ 去重：移除 {removed_count} 篇重复文章")

    return unique_articles


def save_classification_to_db(classification: Dict[str, List[Dict]], db_path: str = DB_PATH):
    """将分类结果保存到数据库"""

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 清空现有的主题表
    cursor.execute("DELETE FROM topics")

    # 插入新的主题
    for topic_name, articles in classification.items():
        # 提取关键词（简化版）
        all_titles = " ".join(a['title'] for a in articles)
        keywords = re.findall(r'[一-鿿]{2,4}|\b[a-zA-Z]{3,}\b', all_titles.lower())
        from collections import Counter
        top_keywords = [kw for kw, _ in Counter(keywords).most_common(10)]

        cursor.execute(
            """INSERT INTO topics (name, keywords, article_count)
               VALUES (?, ?, ?)""",
            (topic_name, json.dumps(top_keywords, ensure_ascii=False), len(articles))
        )

    conn.commit()
    conn.close()

    print(f"\n✓ 分类结果已保存到数据库")


def generate_classification_report(classification: Dict[str, List[Dict]]) -> None:
    """生成分类报告"""

    print(f"\n{'='*70}")
    print(f"📊 智能分类结果")
    print(f"{'='*70}\n")

    total_articles = sum(len(arts) for arts in classification.values())
    print(f"总文章数: {total_articles}")
    print(f"分类数量: {len(classification)}\n")

    # 按文章数排序
    sorted_topics = sorted(classification.items(), key=lambda x: len(x[1]), reverse=True)

    for i, (topic, articles) in enumerate(sorted_topics, 1):
        print(f"{i}. 【{topic}】 {len(articles)} 篇")

        # 显示前5篇
        for j, article in enumerate(articles[:5], 1):
            title = article['title'][:70]
            print(f"   {j}. {title}")

        if len(articles) > 5:
            print(f"   ... 还有 {len(articles)-5} 篇")
        print()

    # 保存到文件
    report = {
        'total_articles': total_articles,
        'topics_count': len(classification),
        'topics': {
            topic: {
                'count': len(arts),
                'samples': [a['title'] for a in arts[:5]]
            }
            for topic, arts in sorted_topics
        }
    }

    report_file = Path("classification_result.json")
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"✓ 详细报告已保存到: {report_file}\n")


def main():
    import argparse

    parser = argparse.ArgumentParser(description='智能分类升级')
    parser.add_argument('--method', choices=['keyword', 'llm', 'hybrid'], default='hybrid',
                        help='分类方法：keyword(关键词), llm(大模型), hybrid(混合，默认)')
    parser.add_argument('--limit', type=int, help='限制处理的文章数量')
    parser.add_argument('--save-db', action='store_true', help='保存分类结果到数据库')

    args = parser.parse_args()

    print("🔍 正在加载文章...")
    articles = load_articles_from_db(limit=args.limit)

    if not articles:
        print("❌ 数据库中没有找到文章")
        return

    print(f"✓ 已加载 {len(articles)} 篇文章\n")

    # 去重
    print("🔄 正在去重...")
    articles = merge_duplicate_articles(articles)
    print(f"✓ 去重后剩余 {len(articles)} 篇文章\n")

    # 分类
    classification = {}

    if args.method in ['keyword', 'hybrid']:
        print("📋 使用关键词分类...")
        classification = batch_articles_by_keyword(articles, top_n=30)
        print(f"✓ 关键词分类完成：{len(classification)} 个主题\n")

    if args.method in ['llm', 'hybrid']:
        print("🤖 使用 LLM 智能分类...")
        llm_classification = classify_with_llm(articles)

        if llm_classification:
            if args.method == 'llm':
                classification = llm_classification
            else:
                # 混合模式：优先使用 LLM 分类
                classification.update(llm_classification)
            print(f"✓ LLM 分类完成\n")

    if not classification:
        print("❌ 分类失败")
        return

    # 生成报告
    generate_classification_report(classification)

    # 保存到数据库
    if args.save_db:
        save_classification_to_db(classification)

    print("💡 下一步建议:")
    print("   1. 查看 classification_result.json 了解详细分类")
    print("   2. 使用 --save-db 参数将结果保存到数据库")
    print("   3. 根据分类结果优化 topics.yaml 配置文件")


if __name__ == "__main__":
    main()
