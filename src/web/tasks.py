"""
后台任务管理模块

使用 asyncio 和 FastAPI BackgroundTasks 替代 subprocess，
提供协作式取消、进度跟踪和错误处理。
"""

import asyncio
import threading
import traceback
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, Optional, List

from rich.console import Console

from ..cache import CacheManager
from ..config import ConfigManager
from ..orchestrator import run_distillation

console = Console()


class TaskStatus(str, Enum):
    """任务状态"""
    IDLE = "idle"
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    STOPPING = "stopping"


class DistillationCancelled(Exception):
    """蒸馏取消信号异常"""
    pass


class DistillTask:
    """蒸馏任务（支持协作式取消）"""

    def __init__(
        self,
        provider: str,
        incremental: bool = True,
        limit: Optional[int] = None,
    ):
        self.provider = provider
        self.incremental = incremental
        self.limit = limit

        self.status = TaskStatus.PENDING
        self.started_at: Optional[datetime] = None
        self.finished_at: Optional[datetime] = None
        self.error: Optional[str] = None
        self.logs: List[str] = []
        self.log_seq: int = 0
        self.current_step: str = "idle"

        self._task: Optional[asyncio.Task] = None
        # 协作式取消信号
        self._cancel_event = threading.Event()

    def is_cancelled(self) -> bool:
        """检查是否已请求取消"""
        return self._cancel_event.is_set()

    def check_cancelled(self):
        """在关键点调用：如果已取消则抛出异常"""
        if self._cancel_event.is_set():
            raise DistillationCancelled("蒸馏任务已被用户取消")

    def add_log(self, message: str):
        """添加日志（通过 callback 调用，不依赖 stdout 重定向）"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.logs.append(log_entry)
        self.log_seq += 1
        if len(self.logs) > 1000:
            self.logs = self.logs[-1000:]

        # 根据日志内容更新当前步骤
        if "步骤 1/4" in message or "从数据库加载" in message:
            self.current_step = "fetch"
        elif "步骤 2/4" in message or "清洗文章" in message:
            self.current_step = "clean"
        elif "步骤 3/4" in message or "主题分类" in message:
            self.current_step = "classify"
        elif "步骤 4/4" in message or "知识合成" in message:
            self.current_step = "synthesize"

    async def run(self):
        """运行任务"""
        if self.status == TaskStatus.RUNNING:
            raise RuntimeError("任务已在运行")

        self.status = TaskStatus.RUNNING
        self.started_at = datetime.now()
        self.error = None
        self.add_log("任务开始...")

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._run_distillation_sync)

            if self._cancel_event.is_set():
                self.status = TaskStatus.CANCELLED
                self.add_log("任务已取消")
            else:
                self.status = TaskStatus.COMPLETED
                self.add_log("✓ 任务完成")

        except DistillationCancelled:
            self.status = TaskStatus.CANCELLED
            self.add_log("任务已取消")

        except Exception as e:
            self.status = TaskStatus.FAILED
            self.error = str(e)
            self.add_log(f"✗ 任务失败: {e}")
            traceback.print_exc()

        finally:
            self.finished_at = datetime.now()

    def _log_callback(self, message: str):
        """日志回调：替代 redirect_stdout/stderr，显式传给 add_log"""
        filter_keywords = ["INFO:", "127.0.0.1:", "HTTP/1.1"]
        stripped = message.strip() if message else ""
        if stripped and not any(kw in stripped for kw in filter_keywords):
            self.add_log(stripped)

    def _run_distillation_sync(self):
        """同步执行蒸馏任务（在线程池中运行）"""
        config_manager = ConfigManager()
        cache_manager = CacheManager()

        # 创建自定义 Console 捕获输出（不修改进程级 stdout/stderr）
        from rich.console import Console as RichConsole
        import io
        log_stream = io.StringIO()
        custom_console = RichConsole(file=log_stream, force_terminal=False)

        try:
            run_distillation(
                config_manager=config_manager,
                cache=cache_manager,
                model=self.provider,
                incremental=self.incremental,
                limit=self.limit,
                console=custom_console,
                cancel_event=self._cancel_event,
            )
        except DistillationCancelled:
            raise
        finally:
            # 捕获 console 输出到日志
            output = log_stream.getvalue()
            if output:
                for line in output.splitlines():
                    if line.strip():
                        self._log_callback(line)

    def cancel(self):
        """请求取消任务（协作式：只设置事件，不强杀线程）"""
        self._cancel_event.set()
        if self.status == TaskStatus.RUNNING:
            self.status = TaskStatus.STOPPING
        self.add_log("正在取消任务...")

    def get_progress(self) -> Dict:
        """获取任务进度信息"""
        cache_dir = Path(".cache")

        topics_done = []
        if (cache_dir / "final").exists():
            topics_done = [
                f.stem.replace("_final", "")
                for f in (cache_dir / "final").glob("*.txt")
            ]

        return {
            "status": self.status.value,
            "step": self.current_step,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "error": self.error,
            "cache": {
                "articles_cached": (cache_dir / "articles.json").exists(),
                "cleaned_cached": (cache_dir / "cleaned.json").exists(),
                "topics_cached": (cache_dir / "topics.json").exists(),
                "batch_count": len(list((cache_dir / "batches").glob("*.txt")))
                if (cache_dir / "batches").exists()
                else 0,
                "final_count": len(topics_done),
            },
            "topics_done": topics_done,
            "log_count": len(self.logs),
        }


class TaskManager:
    """任务管理器（单例）"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._current_task: Optional[DistillTask] = None
        self._initialized = True

    def start_task(
        self,
        provider: str,
        incremental: bool = True,
        limit: Optional[int] = None,
    ) -> DistillTask:
        """启动新任务"""
        # PENDING、RUNNING、STOPPING 都视为占用状态
        if self._current_task and self._current_task.status in (
            TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.STOPPING
        ):
            raise RuntimeError("已有任务在运行")

        task = DistillTask(provider=provider, incremental=incremental, limit=limit)
        self._current_task = task

        # 在后台启动任务
        task._task = asyncio.create_task(task.run())

        return task

    def get_current_task(self) -> Optional[DistillTask]:
        """获取当前任务"""
        return self._current_task

    def stop_task(self):
        """停止当前任务（协作式取消）"""
        if self._current_task:
            self._current_task.cancel()


# 全局任务管理器实例
_task_manager = TaskManager()


def get_task_manager() -> TaskManager:
    """获取任务管理器实例"""
    return _task_manager
