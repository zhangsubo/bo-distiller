"""
Web 服务共享工具

从 web_ui.py 平移而来的公共辅助函数
"""

from pathlib import Path


def _get_storage():
    """延迟导入 SQLiteStorage"""
    import sys
    # 项目根目录（src/web/deps.py 向上三级）
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from src.storage import get_storage
    return get_storage()


def _article_to_dict(article) -> dict:
    """Article 对象转 dict"""
    return {
        "id": article.id,
        "title": article.title,
        "content": article.content,
        "url": article.url,
        "source_type": article.source.type.value if hasattr(article.source.type, 'value') else str(article.source.type),
        "source_name": article.source.name,
        "source_identifier": article.source.identifier,
        "author": article.author,
        "published_date": article.published_date.isoformat() if article.published_date else None,
        "fetched_date": article.fetched_date.isoformat() if article.fetched_date else None,
        "metadata": article.metadata,
    }
