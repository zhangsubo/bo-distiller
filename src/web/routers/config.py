"""
配置与内容源 API

从 web_ui.py 平移而来，保持原有端点行为不变
"""

from pathlib import Path

import yaml
from fastapi import APIRouter, HTTPException

router = APIRouter()


# ==================== 配置 API ====================

@router.get("/api/config")
async def get_config():
    """获取配置"""
    config_file = Path("config.yaml")
    if not config_file.exists():
        config_file = Path("config.example.yaml")
    try:
        with open(config_file, encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return {"config": config, "status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/config")
async def update_config(config: dict):
    """更新配置"""
    try:
        with open("config.yaml", "w", encoding="utf-8") as f:
            yaml.dump(config, f, allow_unicode=True)
        return {"status": "ok", "message": "配置已保存"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 内容源 API ====================

@router.get("/api/sources")
async def get_sources():
    """获取内容源列表"""
    sources_file = Path("sources.yaml")
    if not sources_file.exists():
        return {"sources": []}
    try:
        with open(sources_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return {"sources": data.get("sources", [])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/sources")
async def save_sources(body: dict):
    """保存内容源列表（全量替换）"""
    sources_file = Path("sources.yaml")
    try:
        data = {"sources": body.get("sources", [])}
        with open(sources_file, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
