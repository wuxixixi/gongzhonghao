"""监控与日志 API 蓝图"""

import re

from flask import Blueprint, request, jsonify, Response, stream_with_context
from flask_jwt_extended import jwt_required, get_jwt

from web.extensions import db
from web.models.task_history import TaskHistory
from web.services import monitor_service

monitor_bp = Blueprint("monitor", __name__)


def _require_admin():
    claims = get_jwt()
    return claims.get("role") == "admin"


@monitor_bp.route("/status", methods=["GET"])
@jwt_required()
def system_status():
    """系统状态总览"""
    status = monitor_service.get_system_status()
    return jsonify(code=0, message="ok", data=status)


@monitor_bp.route("/tasks", methods=["GET"])
@jwt_required()
def list_tasks():
    """任务历史 (分页)"""
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", 20, type=int)
    page_size = min(page_size, 100)

    query = TaskHistory.query.order_by(TaskHistory.created_at.desc())

    task_type = request.args.get("task_type")
    if task_type:
        query = query.filter_by(task_type=task_type)

    status = request.args.get("status")
    if status:
        query = query.filter_by(status=status)

    total = query.count()
    tasks = query.offset((page - 1) * page_size).limit(page_size).all()

    return jsonify(code=0, message="ok", data={
        "items": [t.to_dict() for t in tasks],
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@monitor_bp.route("/tasks/<int:task_id>", methods=["GET"])
@jwt_required()
def get_task(task_id):
    """单个任务详情"""
    task = db.session.get(TaskHistory, task_id)
    if task is None:
        return jsonify(code=404, message="任务不存在", data=None), 404
    return jsonify(code=0, message="ok", data=task.to_dict())


@monitor_bp.route("/tasks/running", methods=["GET"])
@jwt_required()
def running_tasks():
    """当前运行中的任务"""
    tasks = TaskHistory.query.filter(
        TaskHistory.status.in_(["pending", "running"])
    ).order_by(TaskHistory.created_at.desc()).all()
    return jsonify(code=0, message="ok", data=[t.to_dict() for t in tasks])


@monitor_bp.route("/logs", methods=["GET"])
@jwt_required()
def list_logs():
    """日志文件列表"""
    if not _require_admin():
        return jsonify(code=403, message="权限不足", data=None), 403
    files = monitor_service.list_log_files()
    return jsonify(code=0, message="ok", data=files)


@monitor_bp.route("/logs/<date>", methods=["GET"])
@jwt_required()
def get_logs(date):
    """某日日志内容"""
    if not _require_admin():
        return jsonify(code=403, message="权限不足", data=None), 403
    if not re.match(r"^\d{8}$", date):
        return jsonify(code=400, message="日期格式无效 (YYYYMMDD)", data=None), 400

    level = request.args.get("level")
    keyword = request.args.get("keyword")
    offset = request.args.get("offset", 0, type=int)
    limit = request.args.get("limit", 500, type=int)
    limit = min(limit, 2000)

    result = monitor_service.get_log_content(date, level, keyword, offset, limit)
    return jsonify(code=0, message="ok", data=result)


@monitor_bp.route("/logs/stream", methods=["GET"])
@jwt_required()
def stream_logs():
    """SSE 实时日志流"""
    if not _require_admin():
        return jsonify(code=403, message="权限不足", data=None), 403

    return Response(
        stream_with_context(monitor_service.stream_log_generator()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
