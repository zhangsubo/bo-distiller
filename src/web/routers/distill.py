"""
蒸馏控制 API

使用新的任务管理器替代 subprocess，提供更好的进度跟踪和错误处理。
"""

import asyncio
import json
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from ..tasks import get_task_manager, TaskStatus

router = APIRouter()

# 获取任务管理器
_task_manager = get_task_manager()


# ==================== 蒸馏控制 API ====================

@router.post("/api/distill/start")
async def start_distill(body: dict):
    """启动蒸馏任务"""
    try:
        current_task = _task_manager.get_current_task()
        if current_task and current_task.status == TaskStatus.RUNNING:
            raise HTTPException(status_code=409, detail="蒸馏任务已在运行")

        # model 参数实际是 provider_id（向后兼容旧的 API）
        provider = body.get("model", "minimax")
        incremental = body.get("incremental", True)
        limit = body.get("limit", None)

        task = _task_manager.start_task(
            provider=provider,
            incremental=incremental,
            limit=limit,
        )

        return {
            "status": "ok",
            "message": "蒸馏任务已启动",
            "task": {
                "provider": task.provider,
                "incremental": task.incremental,
                "started_at": task.started_at.isoformat() if task.started_at else None,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/distill/stop")
async def stop_distill():
    """停止蒸馏任务"""
    _task_manager.stop_task()
    return {"status": "ok", "message": "任务已停止"}


@router.get("/api/distill/status")
async def get_distill_status():
    """获取蒸馏状态"""
    try:
        task = _task_manager.get_current_task()

        if not task:
            return {
                "data": {
                    "running": False,
                    "step": "idle",
                    "started_at": None,
                    "error": None,
                    "model": None,
                    "incremental": None,
                    "cache": {
                        "articles_cached": False,
                        "cleaned_cached": False,
                        "topics_cached": False,
                        "batch_count": 0,
                        "final_count": 0,
                    },
                    "topics_done": [],
                }
            }

        progress = task.get_progress()

        return {
            "data": {
                "running": progress["status"] == TaskStatus.RUNNING.value,
                "step": progress["step"],
                "started_at": progress["started_at"],
                "finished_at": progress["finished_at"],
                "error": progress["error"],
                "provider": task.provider,
                "incremental": task.incremental,
                "cache": progress["cache"],
                "topics_done": progress["topics_done"],
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
        task = _task_manager.get_current_task()
        if not task:
            yield f"data: {json.dumps({'error': '没有运行中的任务'})}\n\n"
            return

        # 用单调序号跟踪进度（logs 超过 1000 条会被截断，len 会停在 1000）
        last_log_seq = task.log_seq

        # 先发送最近的50条日志作为初始上下文
        initial_logs = task.logs[-50:] if len(task.logs) > 50 else task.logs
        for log in initial_logs:
            yield f"data: {json.dumps({'log': log})}\n\n"

        heartbeat_counter = 0

        while task.status in [TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.STOPPING]:
            # 发送新日志
            if task.log_seq > last_log_seq:
                new_count = task.log_seq - last_log_seq
                new_logs = task.logs[-new_count:] if new_count < len(task.logs) else task.logs
                for log in new_logs:
                    yield f"data: {json.dumps({'log': log})}\n\n"
                last_log_seq = task.log_seq
                heartbeat_counter = 0  # 重置心跳计数
            else:
                # 没有新日志时发送心跳，防止连接超时
                heartbeat_counter += 1
                if heartbeat_counter >= 10:  # 每5秒发送一次心跳
                    yield f": heartbeat\n\n"
                    heartbeat_counter = 0

            await asyncio.sleep(0.5)

        # 发送完成信号
        yield f"data: {json.dumps({'done': True, 'status': task.status.value})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/api/distill/logs")
async def get_distill_logs(offset: int = 0, limit: int = 100):
    """获取任务日志（分页）"""
    task = _task_manager.get_current_task()

    if not task:
        return {"logs": [], "total": 0}

    logs = task.logs[offset:offset + limit]
    return {
        "logs": logs,
        "total": len(task.logs),
        "offset": offset,
        "limit": limit,
    }
