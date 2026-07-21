"""
蒸馏控制 API

从 web_ui.py 平移而来，保持原有端点行为不变。
蒸馏进程状态为本模块的模块级可变状态。
"""

import asyncio
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

router = APIRouter()

# 项目根目录（src/web/routers/distill.py 向上三级）
_PROJECT_ROOT = Path(__file__).resolve().parents[3]

_distill_process: Optional[subprocess.Popen] = None
_distill_status = {
    "running": False,
    "step": "idle",
    "started_at": None,
    "error": None,
}


# ==================== 蒸馏控制 API ====================

@router.post("/api/distill/start")
async def start_distill(body: dict):
    """启动蒸馏任务"""
    global _distill_process, _distill_status
    try:
        if _distill_status["running"]:
            raise HTTPException(status_code=409, detail="蒸馏任务已在运行")

        model = body.get("model", "minimax")
        incremental = body.get("incremental", True)

        cmd = ["python3", "distill.py", "run", "--model", model]
        if not incremental:
            cmd.append("--full")

        _distill_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=str(_PROJECT_ROOT),
        )
        _distill_status = {
            "running": True,
            "step": "started",
            "started_at": datetime.now().isoformat(),
            "error": None,
        }
        return {"status": "ok", "message": "蒸馏任务已启动"}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/distill/stop")
async def stop_distill():
    """停止蒸馏任务"""
    global _distill_process, _distill_status
    if _distill_process:
        _distill_process.terminate()
        try:
            _distill_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _distill_process.kill()
        _distill_process = None
    _distill_status["running"] = False
    _distill_status["step"] = "stopped"
    return {"status": "ok"}


@router.get("/api/distill/status")
async def get_distill_status():
    """获取蒸馏状态"""
    global _distill_process, _distill_status
    try:
        cache_dir = Path(".cache")

        # 从实际文件状态推断进度
        topics_done = []
        if (cache_dir / "final").exists():
            topics_done = [f.stem for f in (cache_dir / "final").glob("*.txt")]

        # 推断当前步骤
        step = "idle"
        if _distill_status["running"]:
            if (cache_dir / "final").exists() and list((cache_dir / "final").glob("*.txt")):
                step = "synthesize"
            elif (cache_dir / "topics.pkl").exists():
                step = "classify"
            elif (cache_dir / "cleaned.pkl").exists():
                step = "clean"
            elif (cache_dir / "articles.pkl").exists():
                step = "fetch"
            else:
                step = "started"

        # 检查子进程是否已结束
        if _distill_process and _distill_process.poll() is not None:
            _distill_status["running"] = False
            if _distill_process.returncode != 0:
                _distill_status["error"] = f"进程退出码: {_distill_process.returncode}"
            _distill_status["step"] = "done"
            _distill_process = None

        return {
            "data": {
                "running": _distill_status["running"],
                "step": step,
                "started_at": _distill_status["started_at"],
                "error": _distill_status["error"],
                "cache": {
                    "articles_cached": (cache_dir / "articles.pkl").exists(),
                    "cleaned_cached": (cache_dir / "cleaned.pkl").exists(),
                    "topics_cached": (cache_dir / "topics.pkl").exists(),
                    "batch_count": len(list((cache_dir / "batches").glob("*.txt")))
                    if (cache_dir / "batches").exists()
                    else 0,
                    "final_count": len(topics_done),
                },
                "topics_done": topics_done,
            }
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/distill/stream")
async def distill_log_stream():
    """SSE 实时日志流"""

    async def event_generator():
        while _distill_process and _distill_process.poll() is None:
            line = _distill_process.stdout.readline()
            if line:
                yield f"data: {json.dumps({'log': line.strip()})}\n\n"
            else:
                await asyncio.sleep(0.1)
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
