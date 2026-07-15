"""
智能分类器 - 升级版
支持主题聚类、去重、同主题识别
"""

import re
import sqlite3
from collections import Counter, defaultdict
from typing import Dict, List, Any, Tuple, Set
from pathlib import Path

from ..models import Article


class SmartClassifier:
    """智能分类器

    特性：
    1. 基于关键词的快速分类
    2. 识别同一主题/软件的不同文章
    3. 自动去重
    4. 支持层次化分类
    """

    def __init__(self, min_cluster_size: int = 3):
        self.min_cluster_size = min_cluster_size
        self.stopwords = self._load_stopwords()

    def _load_stopwords(self) -> Set[str]:
        """加载停用词"""
        return {
            '的', '了', '在', '是', '和', '有', '我', '不', '你', '他', '她', '它',
            '这个', '那个', '可以', '就是', '但是', '如果', '因为', '所以', '一个',
            '什么', '怎么', '为什么', '一款', '这款', '一个', '这篇',
            'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of', 'and', 'or', 'but'
        }

    def extract_keywords(self, text: str, top_n: int = 10) -> List[Tuple[str, int]]:
        """提取关键词"""
        # 提取中文词（2-4字）
        chinese_words = re.findall(r'[一-鿿]{2,4}', text)
        # 提取英文词
        english_words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())

        all_words = chinese_words + english_words
        words = [w for w in all_words if w not in self.stopwords]

        counter = Counter(words)
        return counter.most_common(top_n)

    def detect_duplicates(self, articles: List[Article]) -> List[List[Article]]:
        """检测重复文章（完全相同的标题）"""
        title_groups = defaultdict(list)

        for article in articles:
            normalized_title = article.title.strip().lower()
            title_groups[normalized_title].append(article)

        # 返回重复的组
        duplicates = [group for group in title_groups.values() if len(group) > 1]
        return duplicates

    def cluster_by_topic(self, articles: List[Article]) -> Dict[str, List[Article]]:
        """按主题聚类

        识别同一软件/工具/主题的不同文章
        """
        # 提取每篇文章的关键词
        article_keywords = {}
        for article in articles:
            text = f"{article.title} {article.content[:500] if article.content else ''}"
            keywords = self.extract_keywords(text, 15)
            article_keywords[article.id] = [kw for kw, _ in keywords]

        # 按主关键词分组
        keyword_groups = defaultdict(list)
        for article in articles:
            title_keywords = self.extract_keywords(article.title, 5)
            if title_keywords:
                main_keyword = title_keywords[0][0]  # 使用最高频的关键词
                if len(main_keyword) >= 2:  # 至少2个字符
                    keyword_groups[main_keyword].append(article)

        # 过滤：只保留有多篇文章的主题
        clusters = {
            kw: arts for kw, arts in keyword_groups.items()
            if len(arts) >= self.min_cluster_size
        }

        # 未分类的文章
        clustered_ids = {a.id for arts in clusters.values() for a in arts}
        unclustered = [a for a in articles if a.id not in clustered_ids]

        if unclustered:
            clusters['其他'] = unclustered

        return clusters

    def identify_software_articles(self, articles: List[Article]) -> Dict[str, List[Article]]:
        """识别关于同一软件/工具的文章

        专门用于识别：
        - OpenClaw 相关文章
        - Claude / Codex 相关文章
        - 其他工具类文章
        """
        # 常见软件/工具名称
        software_patterns = {
            'Claude': [r'\bClaude\b', r'\bclaude\b'],
            'OpenClaw': [r'\bOpenClaw\b', r'\bopenclaw\b'],
            'Codex': [r'\bCodex\b', r'\bcodex\b'],
            'GitHub': [r'\bGitHub\b', r'\bgithub\b'],
            'VSCode': [r'\bVS\s?Code\b', r'\bvscode\b'],
            'Obsidian': [r'\bObsidian\b', r'\bobsidian\b'],
            'Agent': [r'\bAgent\b', r'\bagent\b', r'智能体'],
            'Skill': [r'\bSkill\b', r'\bskill\b'],
            'API': [r'\bAPI\b', r'\bapi\b'],
        }

        software_groups = defaultdict(list)

        for article in articles:
            text = f"{article.title} {article.content[:200] if article.content else ''}"

            matched = False
            for software, patterns in software_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, text):
                        software_groups[software].append(article)
                        matched = True
                        break
                if matched:
                    break

            if not matched:
                software_groups['其他'].append(article)

        # 只保留有多篇文章的分组
        return {
            name: arts for name, arts in software_groups.items()
            if len(arts) >= self.min_cluster_size
        }

    def hierarchical_classify(self, articles: List[Article]) -> Dict[str, Dict[str, List[Article]]]:
        """层次化分类

        第一层：大类（技术、产品、教程等）
        第二层：具体主题（软件名、工具名等）
        """
        # 第一层：大类识别
        categories = {
            '开源项目': [r'开源', r'star', r'github', r'项目'],
            'AI工具': [r'\bai\b', r'agent', r'智能', r'模型', r'\bllm\b'],
            '编程工具': [r'code', r'编程', r'开发', r'ide'],
            '教程指南': [r'教程', r'指南', r'入门', r'实战', r'手把手'],
            '技术文章': [r'技术', r'架构', r'设计', r'实现'],
        }

        category_groups = defaultdict(list)

        for article in articles:
            text = f"{article.title} {article.content[:200] if article.content else ''}".lower()

            matched = False
            for category, patterns in categories.items():
                if any(re.search(p, text, re.IGNORECASE) for p in patterns):
                    category_groups[category].append(article)
                    matched = True
                    break

            if not matched:
                category_groups['其他'].append(article)

        # 第二层：在每个大类中识别具体主题
        hierarchical = {}
        for category, category_articles in category_groups.items():
            if len(category_articles) >= self.min_cluster_size:
                # 识别这个类别中的具体软件/工具
                topics = self.identify_software_articles(category_articles)
                hierarchical[category] = topics

        return hierarchical

    def classify(self, articles: List[Article], method: str = 'keyword') -> Dict[str, List[Article]]:
        """统一分类接口

        Args:
            articles: 文章列表
            method: 分类方法
                - 'keyword': 关键词分类（默认）
                - 'software': 按软件/工具分类
                - 'hierarchical': 层次化分类
        """
        if method == 'keyword':
            return self.cluster_by_topic(articles)
        elif method == 'software':
            return self.identify_software_articles(articles)
        elif method == 'hierarchical':
            # 扁平化层次结构
            hierarchical = self.hierarchical_classify(articles)
            flattened = {}
            for category, topics in hierarchical.items():
                for topic, arts in topics.items():
                    flattened[f"{category}/{topic}"] = arts
            return flattened
        else:
            raise ValueError(f"未知的分类方法: {method}")

    def generate_report(self, classification: Dict[str, List[Article]]) -> str:
        """生成分类报告"""
        lines = ["=" * 70, "📊 分类结果", "=" * 70, ""]

        total = sum(len(arts) for arts in classification.values())
        lines.append(f"总文章数: {total}")
        lines.append(f"分类数: {len(classification)}")
        lines.append("")

        # 按文章数排序
        sorted_topics = sorted(classification.items(), key=lambda x: len(x[1]), reverse=True)

        for i, (topic, articles) in enumerate(sorted_topics, 1):
            lines.append(f"{i}. 【{topic}】 {len(articles)} 篇")

            # 检测是否有重复
            duplicates = self.detect_duplicates(articles)
            if duplicates:
                lines.append(f"   ⚠️  发现 {len(duplicates)} 组重复文章")

            # 显示前3篇
            for j, article in enumerate(articles[:3], 1):
                lines.append(f"   {j}. {article.title[:60]}")

            if len(articles) > 3:
                lines.append(f"   ... 还有 {len(articles)-3} 篇")

            lines.append("")

        return "\n".join(lines)


def classify_articles_from_db(db_path: str, method: str = 'keyword', limit: int = None) -> Dict[str, List[Dict]]:
    """从数据库读取文章并分类

    Args:
        db_path: 数据库路径
        method: 分类方法
        limit: 限制文章数量

    Returns:
        分类结果字典
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = "SELECT * FROM articles ORDER BY fetched_date DESC"
    if limit:
        query += f" LIMIT {limit}"

    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()

    # 转换为 Article 对象
    from ..models import Article, SourceInfo, SourceType

    articles = []
    for row in rows:
        article = Article(
            id=row['id'],
            title=row['title'],
            content=row['content'] or '',
            url=row['url'],
            source=SourceInfo(
                type=SourceType(row['source_type']),
                name=row['source_name'],
                identifier=row['source_identifier'] or '',
            ),
            author=row['author'],
        )
        articles.append(article)

    # 分类
    classifier = SmartClassifier()
    classification = classifier.classify(articles, method=method)

    # 转换回字典（方便序列化）
    result = {}
    for topic, arts in classification.items():
        result[topic] = [
            {
                'id': a.id,
                'title': a.title,
                'url': a.url,
                'source': a.source.name,
            }
            for a in arts
        ]

    return result
