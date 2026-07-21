"""
定时同步 API

查看/修改定时同步配置（写回 config.yaml 的 sync 段并动态调整调度任务）
"""

from pathlib import Path

import yaml
from fastapi import APIRouter, HTTPException

from src.config import get_config_manager
from src.services.scheduler_service import get_next_run_time, reschedule_sync_job
from src.web.deps import _get_storage

router = APIRouter()


# ==================== 定时同步 API ====================

@router.get("/api/sync/status")
async def get_sync_status():
    """获取定时同步状态"""
    try:
        sync_config = get_config_manager().load_config().sync
        storage = _get_storage()
        state = storage.get_sync_state("cubox", "Cubox 收藏") or {}
        return {
            "enabled": sync_config.enabled,
            "interval_minutes": sync_config.interval_minutes,
            "incremental": sync_config.incremental,
            "last_sync": state.get("last_sync"),
            "next_run_time": get_next_run_time(),
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/sync/config")
async def update_sync_config(body: dict):
    """更新定时同步配置（写回 config.yaml 并 reschedule）"""
    try:
        config_file = Path("config.yaml")
        with open(config_file, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        sync_section = data.get("sync", {}) or {}
        for key in ("enabled", "interval_minutes", "incremental"):
            if key in body:
                sync_section[key] = body[key]
        data["sync"] = sync_section

        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True)

        reschedule_sync_job(
            enabled=bool(sync_section.get("enabled", False)),
            interval_minutes=int(sync_section.get("interval_minutes", 60)),
        )
        return {"status": "ok", "message": "同步配置已保存"}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
