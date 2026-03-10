"""异步任务执行器"""

import time
import json
import threading
from concurrent.futures import ThreadPoolExecutor, Future
from datetime import datetime, timezone
from typing import Optional


class TaskRunner:
    """基于线程池的异步任务执行器 (单例)"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._executor = ThreadPoolExecutor(max_workers=2)
        self._running_tasks: dict[int, Future] = {}
        self._initialized = True

    def submit_task(self, task_id: int, task_type: str, func, *args, **kwargs) -> bool:
        """提交异步任务"""
        # 检查同类型任务是否正在运行
        for tid, future in list(self._running_tasks.items()):
            if future.running():
                from flask import current_app
                try:
                    app = current_app._get_current_object()
                except RuntimeError:
                    pass
                # 不阻止提交，但发出警告
                break

        future = self._executor.submit(
            self._run_task_wrapper, task_id, task_type, func, *args, **kwargs
        )
        self._running_tasks[task_id] = future
        return True

    def _run_task_wrapper(self, task_id: int, task_type: str, func, *args, **kwargs):
        """任务包装器 - 管理状态更新"""
        from web import create_app
        app = create_app()

        with app.app_context():
            from web.extensions import db
            from web.models.task_history import TaskHistory

            task = db.session.get(TaskHistory, task_id)
            if not task:
                return

            task.status = "running"
            task.started_at = datetime.now(timezone.utc)
            db.session.commit()

            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time

                task.status = "success"
                task.finished_at = datetime.now(timezone.utc)
                task.duration_seconds = round(elapsed, 2)
                if result and isinstance(result, dict):
                    task.report_json = json.dumps(result, ensure_ascii=False, default=str)
                db.session.commit()
            except Exception as e:
                elapsed = time.time() - start_time
                task.status = "failed"
                task.finished_at = datetime.now(timezone.utc)
                task.duration_seconds = round(elapsed, 2)
                task.error_message = str(e)
                db.session.commit()
            finally:
                self._running_tasks.pop(task_id, None)

    def get_running_task_ids(self) -> list[int]:
        """获取正在运行的任务 ID"""
        return [
            tid for tid, future in self._running_tasks.items()
            if future.running() or not future.done()
        ]

    def is_task_type_running(self, task_type: str) -> bool:
        """检查某类型任务是否正在运行"""
        from web.models.task_history import TaskHistory
        running = TaskHistory.query.filter_by(
            task_type=task_type, status="running"
        ).first()
        return running is not None


task_runner = TaskRunner()
