from fastapi import APIRouter, HTTPException

from src.config import get_config_manager
from src.storage import get_storage

router = APIRouter()


@router.get("/api/topics/config")
async def get_topics_config():
    storage = get_storage()
    topics_data = storage.get_setting("topics")
    if topics_data is None:
        config_manager = get_config_manager()
        config_manager.load_topics()
        topics_data = storage.get_setting("topics") or {}

    # 确保返回的是对象而不是字符串
    if isinstance(topics_data, str):
        import json
        try:
            topics_data = json.loads(topics_data)
        except:
            topics_data = {}

    return {"config": topics_data}


@router.post("/api/topics/config")
async def save_topics_config(config: dict):
    try:
        config_manager = get_config_manager()
        config_manager.save_topics(config)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
