"""
定时同步 API

查看/修改定时同步配置（只写数据库，不修改 config.yaml）
"""

from fastapi import APIRouter, HTTPException

from src.config import get_config_manager
from src.services.scheduler_service import get_next_run_time, reschedule_sync_job
from src.storage import get_storage

router = APIRouter()


@router.get("/api/sync/status")
async def get_sync_status():
    """获取定时同步状态"""
    try:
        sync_config = get_config_manager().load_config().sync
        storage = get_storage()
        state = storage.get_sync_state("cubox", "Cubox 收藏") or {}
        return {
            "enabled": sync_config.enabled,
            "interval_minutes": sync_config.interval_minutes,
            "incremental": sync_config.incremental,
            "last_sync": state.get("last_sync"),
            "next_run_time": get_next_run_time(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/sync/config")
async def update_sync_config(body: dict):
    """更新定时同步配置（只写数据库，不修改 config.yaml）"""
    try:
        storage = get_storage()
        config_manager = get_config_manager()

        # 读取当前数据库配置
        config = config_manager.load_config()

        # 合并 sync 字段
        if "enabled" in body:
            config.sync.enabled = bool(body["enabled"])
        if "interval_minutes" in body:
            config.sync.interval_minutes = int(body["interval_minutes"])
        if "incremental" in body:
            config.sync.incremental = bool(body["incremental"])

        # 验证并保存到数据库
        raw_config = storage.get_setting("system_config") or {}
        if isinstance(raw_config, str):
            import json
            raw_config = json.loads(raw_config)
        raw_config["sync"] = {
            "enabled": config.sync.enabled,
            "interval_minutes": config.sync.interval_minutes,
            "incremental": config.sync.incremental,
        }
        config_manager.save_config(raw_config)

        # 数据库提交成功后再调整调度
        reschedule_sync_job(
            enabled=config.sync.enabled,
            interval_minutes=config.sync.interval_minutes,
        )
        return {"status": "ok", "message": "同步配置已保存"}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
