"""
提示词配置 API

读写项目根目录 prompts.yaml
"""

from pathlib import Path

import yaml
from fastapi import APIRouter, HTTPException

router = APIRouter()


# ==================== 提示词配置 API ====================

@router.get("/api/prompts")
async def get_prompts():
    """获取提示词配置（原样返回 prompts.yaml 内容）"""
    prompts_file = Path("prompts.yaml")
    if not prompts_file.exists():
        return {"prompts": {}}
    try:
        with open(prompts_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return {"prompts": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/prompts")
async def save_prompts(body: dict):
    """保存提示词配置（兼容 {prompts: ...} 包裹或直接提交内容）"""
    try:
        data = body.get("prompts", body)
        with open("prompts.yaml", "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
