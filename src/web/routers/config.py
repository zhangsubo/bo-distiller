from fastapi import APIRouter, HTTPException

from src.config import get_config_manager
from src.storage import get_storage

router = APIRouter()


@router.get("/api/config")
async def get_config():
    storage = get_storage()
    config = storage.get_setting("system_config")
    if config is None:
        config_manager = get_config_manager()
        config_manager.load_config()
        config = storage.get_setting("system_config") or {}

    # 确保返回的是对象而不是字符串
    if isinstance(config, str):
        import json
        config = json.loads(config)

    return {"config": config, "status": "ok"}


@router.post("/api/config")
async def update_config(config: dict):
    try:
        config_manager = get_config_manager()
        config_manager.save_config(config)
        return {"status": "ok", "message": "配置已保存"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/sources")
async def get_sources():
    storage = get_storage()
    sources_data = storage.get_setting("sources")
    if sources_data is None:
        config_manager = get_config_manager()
        config_manager.load_sources()
        sources_data = storage.get_setting("sources") or {}

    # 确保返回的是对象而不是字符串
    if isinstance(sources_data, str):
        import json
        try:
            sources_data = json.loads(sources_data)
        except:
            sources_data = {}

    return {"sources": sources_data.get("sources", [])}


@router.post("/api/sources")
async def save_sources(body: dict):
    try:
        config_manager = get_config_manager()
        config_manager.save_sources(body.get("sources", []))
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
