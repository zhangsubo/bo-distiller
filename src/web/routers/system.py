"""
系统状态 API

从 web_ui.py 平移而来，保持原有端点行为不变
"""

from pathlib import Path

from fastapi import APIRouter

# 注意：必须按模块访问 _distill_status，因为 start_distill 会整体重新赋值该字典，
# 直接 from 导入会持有旧对象的引用
from src.web.routers import distill as distill_router

router = APIRouter()


# ==================== 系统状态 API ====================

@router.get("/api/status")
async def get_status():
    """系统状态"""
    cache_dir = Path(".cache")
    output_dir = Path("output")

    cache_info = {}
    if cache_dir.exists():
        cache_info = {
            "articles": (cache_dir / "articles.pkl").exists(),
            "cleaned": (cache_dir / "cleaned.pkl").exists(),
            "topics": (cache_dir / "topics.pkl").exists(),
        }

    output_count = len(list(output_dir.glob("*.md"))) if output_dir.exists() else 0

    return {
        "cache": cache_info,
        "output_documents": output_count,
        "status": "idle" if not distill_router._distill_status["running"] else "running",
    }
