"""
定时同步调度服务

基于 APScheduler BackgroundScheduler 的模块级单例，
按 config.yaml 的 sync 配置周期执行 Cubox 同步。
"""

import traceback
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from rich.console import Console

from src.config import get_config_manager

console = Console()

# 同步任务的固定 job ID
SYNC_JOB_ID = "cubox_sync"

_scheduler: Optional[BackgroundScheduler] = None


def _run_scheduled_sync():
    """定时任务入口：按当前配置执行同步"""
    from src.services.sync_service import run_sync

    try:
        sync_config = get_config_manager().load_config().sync
        result = run_sync(incremental=sync_config.incremental)
        console.print(f"[green]定时同步完成: {result.get('message')}[/green]")
    except Exception as e:
        console.print(f"[red]定时同步失败: {e}[/red]")
        traceback.print_exc()


def start_scheduler() -> BackgroundScheduler:
    """启动调度器（幂等）

    enabled=false 时不注册 job 但仍启动调度器，便于后续动态开启。
    """
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    _scheduler = BackgroundScheduler()
    sync_config = get_config_manager().load_config().sync
    if sync_config.enabled:
        _scheduler.add_job(
            _run_scheduled_sync,
            IntervalTrigger(minutes=sync_config.interval_minutes),
            id=SYNC_JOB_ID,
            max_instances=1,
            coalesce=True,
            replace_existing=True,
        )
        console.print(
            f"[green]定时同步已启动：每 {sync_config.interval_minutes} 分钟[/green]"
        )
    _scheduler.start()
    return _scheduler


def reschedule_sync_job(enabled: bool, interval_minutes: int):
    """运行时调整同步任务（开关/间隔）"""
    scheduler = start_scheduler()
    if enabled:
        scheduler.add_job(
            _run_scheduled_sync,
            IntervalTrigger(minutes=interval_minutes),
            id=SYNC_JOB_ID,
            max_instances=1,
            coalesce=True,
            replace_existing=True,
        )
    elif scheduler.get_job(SYNC_JOB_ID):
        scheduler.remove_job(SYNC_JOB_ID)


def shutdown_scheduler():
    """关闭调度器（不等待任务完成）"""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None


def get_next_run_time() -> Optional[str]:
    """获取同步任务下次执行时间（ISO 格式），无任务时返回 None"""
    if _scheduler is None:
        return None
    job = _scheduler.get_job(SYNC_JOB_ID)
    if job and job.next_run_time:
        return job.next_run_time.isoformat()
    return None
