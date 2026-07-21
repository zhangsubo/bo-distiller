"""
主题配置 API

从 web_ui.py 平移而来，保持原有端点行为不变
"""

from pathlib import Path

import yaml
from fastapi import APIRouter, HTTPException

router = APIRouter()


# ==================== 主题配置 API ====================

@router.get("/api/topics/config")
async def get_topics_config():
    """获取 topics.yaml 配置"""
    topics_file = Path("topics.yaml")
    if not topics_file.exists():
        return {"config": {}}
    try:
        with open(topics_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return {"config": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/topics/config")
async def save_topics_config(config: dict):
    """保存 topics.yaml 配置"""
    try:
        with open("topics.yaml", "w", encoding="utf-8") as f:
            yaml.dump(config, f, allow_unicode=True)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
