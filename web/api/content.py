"""内容管理 API 蓝图"""

import re

from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity

from web.services import content_service
from web.services import pipeline_service
from web.extensions import limiter

content_bp = Blueprint("content", __name__)


@content_bp.route("/articles", methods=["GET"])
@jwt_required()
def list_articles():
    """文章列表 (分页)"""
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", 20, type=int)
    page_size = min(page_size, 100)
    result = content_service.list_article_dates(page, page_size)
    return jsonify(code=0, message="ok", data=result)


@content_bp.route("/articles/<date>", methods=["GET"])
@jwt_required()
def get_article(date):
    """某日文章详情"""
    if not re.match(r"^\d{6}$", date):
        return jsonify(code=400, message="日期格式无效", data=None), 400
    detail = content_service.get_article_detail(date)
    if detail is None:
        return jsonify(code=404, message="文章不存在", data=None), 404
    return jsonify(code=0, message="ok", data=detail)


@content_bp.route("/articles/<date>", methods=["PUT"])
@jwt_required()
def update_article(date):
    """编辑文章"""
    if not re.match(r"^\d{6}$", date):
        return jsonify(code=400, message="日期格式无效", data=None), 400
    data = request.get_json(silent=True) or {}
    content_markdown = data.get("content_markdown", "")
    if not content_markdown:
        return jsonify(code=400, message="内容不能为空", data=None), 400
    ok = content_service.update_article(date, content_markdown)
    if not ok:
        return jsonify(code=404, message="文章不存在", data=None), 404
    return jsonify(code=0, message="保存成功", data=None)


@content_bp.route("/articles/<date>", methods=["DELETE"])
@jwt_required()
def delete_article(date):
    """删除某日文章"""
    if not re.match(r"^\d{6}$", date):
        return jsonify(code=400, message="日期格式无效", data=None), 400
    ok = content_service.delete_article(date)
    if not ok:
        return jsonify(code=404, message="目录不存在", data=None), 404
    return jsonify(code=0, message="删除成功", data=None)


@content_bp.route("/articles/<date>/images/<filename>", methods=["GET"])
@jwt_required()
def get_image(date, filename):
    """获取文章图片"""
    if not re.match(r"^\d{6}$", date):
        return jsonify(code=400, message="日期格式无效", data=None), 400
    path = content_service.get_image_path(date, filename)
    if path is None:
        return jsonify(code=404, message="图片不存在", data=None), 404
    return send_file(str(path), mimetype="image/png")


@content_bp.route("/articles/<date>/raw-data", methods=["GET"])
@jwt_required()
def get_raw_data(date):
    """获取原始采集数据"""
    if not re.match(r"^\d{6}$", date):
        return jsonify(code=400, message="日期格式无效", data=None), 400
    data = content_service.get_json_data(date, "raw_data.json")
    if data is None:
        return jsonify(code=404, message="数据不存在", data=None), 404
    return jsonify(code=0, message="ok", data=data)


@content_bp.route("/articles/<date>/selected-data", methods=["GET"])
@jwt_required()
def get_selected_data(date):
    """获取筛选数据"""
    if not re.match(r"^\d{6}$", date):
        return jsonify(code=400, message="日期格式无效", data=None), 400
    data = content_service.get_json_data(date, "selected_data.json")
    if data is None:
        return jsonify(code=404, message="数据不存在", data=None), 404
    return jsonify(code=0, message="ok", data=data)


@content_bp.route("/articles/<date>/report", methods=["GET"])
@jwt_required()
def get_report(date):
    """获取运行报告"""
    if not re.match(r"^\d{6}$", date):
        return jsonify(code=400, message="日期格式无效", data=None), 400
    data = content_service.get_json_data(date, "run_report.json")
    if data is None:
        return jsonify(code=404, message="报告不存在", data=None), 404
    return jsonify(code=0, message="ok", data=data)


@content_bp.route("/generate/daily", methods=["POST"])
@jwt_required()
@limiter.limit("2/10minutes")
def generate_daily():
    """触发每日热点生成"""
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    skip_publish = data.get("skip_publish", False)
    force = data.get("force", False)
    result = pipeline_service.trigger_daily_pipeline(user_id, skip_publish, force)
    if "error" in result:
        return jsonify(code=409, message=result["error"], data=None), 409
    return jsonify(code=0, message="任务已提交", data=result)


@content_bp.route("/generate/deep-analysis", methods=["POST"])
@jwt_required()
@limiter.limit("2/10minutes")
def generate_deep_analysis():
    """触发深度分析生成"""
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    skip_publish = data.get("skip_publish", False)
    result = pipeline_service.trigger_deep_analysis(user_id, skip_publish)
    if "error" in result:
        return jsonify(code=409, message=result["error"], data=None), 409
    return jsonify(code=0, message="任务已提交", data=result)


@content_bp.route("/deep-analysis", methods=["GET"])
@jwt_required()
def list_deep_analysis():
    """深度分析文章列表"""
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", 20, type=int)
    result = content_service.list_deep_analysis(page, page_size)
    return jsonify(code=0, message="ok", data=result)


@content_bp.route("/deep-analysis/<date>", methods=["GET"])
@jwt_required()
def get_deep_analysis(date):
    """深度分析文章详情"""
    if not re.match(r"^\d{6}$", date):
        return jsonify(code=400, message="日期格式无效", data=None), 400
    detail = content_service.get_deep_analysis_detail(date)
    if detail is None:
        return jsonify(code=404, message="深度分析不存在", data=None), 404
    return jsonify(code=0, message="ok", data=detail)


@content_bp.route("/deep-analysis/<date>/images/<filename>", methods=["GET"])
@jwt_required()
def get_deep_image(date, filename):
    """获取深度分析图片"""
    if not re.match(r"^\d{6}$", date):
        return jsonify(code=400, message="日期格式无效", data=None), 400
    path = content_service.get_deep_image_path(date, filename)
    if path is None:
        return jsonify(code=404, message="图片不存在", data=None), 404
    return send_file(str(path), mimetype="image/png")
