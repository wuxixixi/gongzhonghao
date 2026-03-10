"""流水线服务 - 桥接 Flask 与现有 Pipeline 模块"""

from datetime import datetime, timezone

from web.extensions import db
from web.models.task_history import TaskHistory
from web.tasks.task_runner import task_runner


def trigger_daily_pipeline(user_id: int, skip_publish: bool = False, force: bool = False) -> dict:
    """触发每日热点流水线"""
    if task_runner.is_task_type_running("daily_hot"):
        return {"error": "已有每日热点任务正在运行"}

    today = datetime.now().strftime("%y%m%d")
    task = TaskHistory(
        task_type="daily_hot",
        status="pending",
        triggered_by=user_id,
        article_date=today,
    )
    db.session.add(task)
    db.session.commit()

    task_runner.submit_task(
        task.id, "daily_hot",
        _run_daily_pipeline, skip_publish, force
    )
    return {"task_id": task.id, "status": "pending"}


def trigger_deep_analysis(user_id: int, skip_publish: bool = False) -> dict:
    """触发深度分析生成"""
    if task_runner.is_task_type_running("deep_analysis"):
        return {"error": "已有深度分析任务正在运行"}

    today = datetime.now().strftime("%y%m%d")
    task = TaskHistory(
        task_type="deep_analysis",
        status="pending",
        triggered_by=user_id,
        article_date=today,
    )
    db.session.add(task)
    db.session.commit()

    task_runner.submit_task(
        task.id, "deep_analysis",
        _run_deep_analysis, skip_publish
    )
    return {"task_id": task.id, "status": "pending"}


def _run_daily_pipeline(skip_publish: bool = False, force: bool = False) -> dict:
    """执行每日热点流水线 (在后台线程中运行)"""
    import sys
    import os

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from scripts.pipeline import Pipeline
    pipeline = Pipeline()
    report = pipeline.run(skip_publish=skip_publish, force_regenerate=force)
    return report if isinstance(report, dict) else {"status": "success"}


def _run_deep_analysis(skip_publish: bool = False) -> dict:
    """执行深度分析 (在后台线程中运行)"""
    import sys
    import os

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from auto_generator import AutoArticleGenerator
    generator = AutoArticleGenerator()
    report = generator.generate(skip_publish=skip_publish, wait_time=False)
    return report if isinstance(report, dict) else {"status": "success"}
