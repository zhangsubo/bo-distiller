from src.storage import get_storage


def _get_storage():
    return get_storage()


def _article_to_dict(article) -> dict:
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
