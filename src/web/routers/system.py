"""
系统状态 API

通过 TaskManager 获取真实蒸馏状态
"""

from pathlib import Path

from fastapi import APIRouter

from src.web.tasks import get_task_manager, TaskStatus

router = APIRouter()


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

    # 从 TaskManager 获取真实状态
    task = get_task_manager().get_current_task()
    is_running = task is not None and task.status == TaskStatus.RUNNING

    return {
        "cache": cache_info,
        "output_documents": output_count,
        "status": "running" if is_running else "idle",
    }
