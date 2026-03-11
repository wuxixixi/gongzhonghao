"""发布管理 API 蓝图"""

import re

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity

from web.services import publish_service
from web.extensions import limiter

publish_bp = Blueprint("publish", __name__)


def _require_admin():
    claims = get_jwt()
    return claims.get("role") == "admin"


@publish_bp.route("/draft/<date>", methods=["POST"])
@jwt_required()
@limiter.limit("2/10minutes")
def create_draft(date):
    """为指定日期文章创建微信草稿"""
    if not _require_admin():
        return jsonify(code=403, message="权限不足", data=None), 403
    if not re.match(r"^\d{6}$", date):
        return jsonify(code=400, message="日期格式无效", data=None), 400

    data = request.get_json(silent=True) or {}
    article_type = data.get("article_type", "daily_hot")
    user_id = int(get_jwt_identity())

    result = publish_service.create_draft(date, article_type, user_id)
    if "error" in result:
        return jsonify(code=500, message=result["error"], data=None), 500
    return jsonify(code=0, message="草稿创建成功", data=result)


@publish_bp.route("/records", methods=["GET"])
@jwt_required()
def list_records():
    """发布记录列表"""
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", 20, type=int)
    result = publish_service.list_records(page, page_size)
    return jsonify(code=0, message="ok", data=result)


@publish_bp.route("/wechat/token-status", methods=["GET"])
@jwt_required()
def token_status():
    """微信 Token 状态"""
    if not _require_admin():
        return jsonify(code=403, message="权限不足", data=None), 403
    status = publish_service.get_wechat_token_status()
    return jsonify(code=0, message="ok", data=status)


@publish_bp.route("/wechat/refresh-token", methods=["POST"])
@jwt_required()
@limiter.limit("3/minute")
def refresh_token():
    """强制刷新微信 Token"""
    if not _require_admin():
        return jsonify(code=403, message="权限不足", data=None), 403
    result = publish_service.refresh_wechat_token()
    if result.get("success"):
        return jsonify(code=0, message="Token 刷新成功", data=result)
    return jsonify(code=500, message=result.get("error", "刷新失败"), data=None), 500
