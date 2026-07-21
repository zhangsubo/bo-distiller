"""
文章与 Cubox 同步 API

从 web_ui.py 平移而来，保持原有端点行为不变
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from src.web.deps import _article_to_dict, _get_storage

router = APIRouter()


# ==================== 文章 API ====================

@router.get("/api/articles")
async def list_articles(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    source_type: Optional[str] = None,
):
    """分页文章列表"""
    try:
        storage = _get_storage()
        offset = (page - 1) * page_size

        if search:
            all_articles = storage.search_articles(search)
            total = len(all_articles)
            articles = all_articles[offset:offset + page_size]
        elif source_type:
            all_articles = storage.get_articles_by_source(source_type)
            total = len(all_articles)
            articles = all_articles[offset:offset + page_size]
        else:
            total = storage.get_article_count()
            articles = storage.get_all_articles(limit=page_size, offset=offset)

        return {
            "data": [_article_to_dict(a) for a in articles],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size,
            },
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/articles/stats")
async def get_article_stats():
    """文章统计"""
    try:
        storage = _get_storage()
        stats = storage.get_stats()
        return {"data": stats}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/articles/{article_id}")
async def get_article(article_id: str):
    """获取单篇文章"""
    storage = _get_storage()
    article = storage.get_article(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    return {"data": _article_to_dict(article)}


@router.delete("/api/articles/{article_id}")
async def delete_article(article_id: str):
    """删除文章"""
    storage = _get_storage()
    success = storage.delete_article(article_id)
    if not success:
        raise HTTPException(status_code=404, detail="文章不存在")
    return {"status": "ok"}


# ==================== Cubox 同步 API ====================

@router.post("/api/articles/sync")
async def sync_cubox():
    """同步 Cubox 收藏（逻辑在 sync_service.run_sync，响应结构保持不变）"""
    try:
        from src.services.sync_service import run_sync

        return run_sync()
    except ValueError as e:
        # Cubox CLI 不可用
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
