from fastapi import APIRouter, HTTPException

from src.config import get_config_manager
from src.storage import get_storage

router = APIRouter()


@router.get("/api/prompts")
async def get_prompts():
    storage = get_storage()
    prompts_data = storage.get_setting("prompts")
    if prompts_data is None:
        config_manager = get_config_manager()
        config_manager.load_prompts()
        prompts_data = storage.get_setting("prompts") or {}

    # 确保返回的是对象而不是字符串
    if isinstance(prompts_data, str):
        import json
        try:
            prompts_data = json.loads(prompts_data)
        except:
            prompts_data = {}

    return {"prompts": prompts_data}


@router.post("/api/prompts")
async def save_prompts(body: dict):
    try:
        data = body.get("prompts", body)
        config_manager = get_config_manager()
        config_manager.save_prompts(data)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
