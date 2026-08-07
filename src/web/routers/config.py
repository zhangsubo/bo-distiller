import copy
import json

from fastapi import APIRouter, HTTPException

from src.config import get_config_manager
from src.storage import get_storage

router = APIRouter()

# 掩码占位符：前端提交此值时表示"保留旧 Key"
_KEY_PLACEHOLDER = "***已配置***"


def _mask_api_keys(config: dict) -> dict:
    """将 llm.providers.*.api_key 替换为掩码占位符（不修改原对象）"""
    masked = copy.deepcopy(config)
    providers = masked.get("llm", {}).get("providers", {})
    for provider_cfg in providers.values():
        if isinstance(provider_cfg, dict) and provider_cfg.get("api_key"):
            provider_cfg["api_key"] = _KEY_PLACEHOLDER
    return masked


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
        config = json.loads(config)

    # 脱敏：不向浏览器返回明文 API Key
    return {"config": _mask_api_keys(config), "status": "ok"}


@router.post("/api/config")
async def update_config(body: dict):
    try:
        storage = get_storage()
        config_manager = get_config_manager()

        # 合并旧 Key：空值或掩码占位符保留数据库中的旧值
        old_config = storage.get_setting("system_config") or {}
        if isinstance(old_config, str):
            old_config = json.loads(old_config)
        old_providers = old_config.get("llm", {}).get("providers", {})

        new_providers = body.get("llm", {}).get("providers", {})
        for pid, new_cfg in new_providers.items():
            if not isinstance(new_cfg, dict):
                continue
            new_key = new_cfg.get("api_key", "")
            # 空值或掩码 → 保留旧 Key
            if not new_key or new_key == _KEY_PLACEHOLDER:
                old_key = old_providers.get(pid, {}).get("api_key", "")
                new_cfg["api_key"] = old_key

        # 验证并保存
        config_manager.save_config(body)
        return {"status": "ok", "message": "配置已保存"}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
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
