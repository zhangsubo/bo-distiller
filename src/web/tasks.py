"""
后台任务管理模块

使用 asyncio 和 FastAPI BackgroundTasks 替代 subprocess，
提供更好的进度跟踪和错误处理。
"""

import asyncio
import traceback
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Optional, List

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


class DistillTask:
    """蒸馏任务"""

    def __init__(
        self,
        provider: str,
        incremental: bool = True,
        limit: Optional[int] = None,
    ):
        self.provider = provider  # 提供商 ID
        self.incremental = incremental
        self.limit = limit

        self.status = TaskStatus.IDLE
        self.started_at: Optional[datetime] = None
        self.finished_at: Optional[datetime] = None
        self.error: Optional[str] = None
        self.logs: List[str] = []
        # 单调递增日志序号：logs 列表会按 1000 条截断，len(logs) 会停在 1000，
        # SSE 必须用它而不是 len(logs) 来判断是否有新日志
        self.log_seq: int = 0
        self.current_step: str = "idle"

        self._task: Optional[asyncio.Task] = None
        self._cancelled = False

    def add_log(self, message: str):
        """添加日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.logs.append(log_entry)
        self.log_seq += 1
        if len(self.logs) > 1000:  # 限制日志条数
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
            # 在后台线程中运行同步函数
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self._run_distillation_sync,
            )

            if not self._cancelled:
                self.status = TaskStatus.COMPLETED
                self.add_log("✓ 任务完成")

        except Exception as e:
            self.status = TaskStatus.FAILED
            self.error = str(e)
            self.add_log(f"✗ 任务失败: {e}")
            traceback.print_exc()

        finally:
            self.finished_at = datetime.now()

    def _run_distillation_sync(self):
        """同步执行蒸馏任务（在线程池中运行）"""
        try:
            config_manager = ConfigManager()
            cache_manager = CacheManager()

            # 创建一个自定义 console 来捕获输出
            import io
            from contextlib import redirect_stdout, redirect_stderr

            # 捕获输出并添加到日志
            class LogCapture:
                def __init__(self, task):
                    self.task = task
                    # 定义需要过滤掉的日志关键词
                    self.filter_keywords = [
                        "使用缓存:",
                        "已缓存",
                        "INFO:",
                        "127.0.0.1:",
                        "HTTP/1.1",
                    ]

                def write(self, text):
                    if text and text.strip():
                        # 过滤掉非蒸馏相关的日志
                        stripped = text.strip()
                        if not any(keyword in stripped for keyword in self.filter_keywords):
                            self.task.add_log(stripped)

                def flush(self):
                    pass

            log_capture = LogCapture(self)

            with redirect_stdout(log_capture), redirect_stderr(log_capture):
                run_distillation(
                    config_manager=config_manager,
                    cache=cache_manager,
                    model=self.provider,  # 传递 provider ID
                    incremental=self.incremental,
                    limit=self.limit,
                    console=console,
                )

        except Exception as e:
            raise e

    def cancel(self):
        """取消任务"""
        self._cancelled = True
        if self._task and not self._task.done():
            self._task.cancel()
        self.status = TaskStatus.CANCELLED
        self.add_log("任务已取消")

    def get_progress(self) -> Dict:
        """获取任务进度信息"""
        cache_dir = Path(".cache")

        # 从缓存推断进度
        topics_done = []
        if (cache_dir / "final").exists():
            # 移除文件名中的 _final 后缀
            topics_done = [
                f.stem.replace("_final", "")
                for f in (cache_dir / "final").glob("*.txt")
            ]

        # 使用实时跟踪的步骤，而不是推断
        step = self.current_step if self.status == TaskStatus.RUNNING else self.current_step

        return {
            "status": self.status.value,
            "step": step,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "error": self.error,
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
        if self._current_task and self._current_task.status == TaskStatus.RUNNING:
            raise RuntimeError("已有任务在运行")

        # 创建新任务
        task = DistillTask(provider=provider, incremental=incremental, limit=limit)
        self._current_task = task

        # 在后台启动任务
        task._task = asyncio.create_task(task.run())

        return task

    def get_current_task(self) -> Optional[DistillTask]:
        """获取当前任务"""
        return self._current_task

    def stop_task(self):
        """停止当前任务"""
        if self._current_task:
            self._current_task.cancel()


# 全局任务管理器实例
_task_manager = TaskManager()


def get_task_manager() -> TaskManager:
    """获取任务管理器实例"""
    return _task_manager
