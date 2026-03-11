"""配置管理 API 蓝图"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt

from web.services import config_service
from web.extensions import limiter

config_bp = Blueprint("config", __name__)


def _require_admin():
    claims = get_jwt()
    return claims.get("role") == "admin"


@config_bp.route("", methods=["GET"])
@jwt_required()
def get_all():
    """获取所有配置 (按 category 分组)"""
    if not _require_admin():
        return jsonify(code=403, message="权限不足", data=None), 403
    configs = config_service.get_all_configs(mask_secret=True)
    return jsonify(code=0, message="ok", data=configs)


@config_bp.route("/<category>", methods=["GET"])
@jwt_required()
def get_category(category):
    """获取某类别配置"""
    if not _require_admin():
        return jsonify(code=403, message="权限不足", data=None), 403
    configs = config_service.get_category_configs(category, mask_secret=True)
    if configs is None:
        return jsonify(code=404, message="类别不存在", data=None), 404
    return jsonify(code=0, message="ok", data=configs)


@config_bp.route("/<category>", methods=["PUT"])
@jwt_required()
def update_category(category):
    """批量更新某类别配置"""
    if not _require_admin():
        return jsonify(code=403, message="权限不足", data=None), 403

    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify(code=400, message="请提供更新数据", data=None), 400

    ok = config_service.update_category_configs(category, data)
    if not ok:
        return jsonify(code=404, message="类别不存在", data=None), 404
    return jsonify(code=0, message="配置已更新", data=None)


@config_bp.route("/test/llm", methods=["POST"])
@jwt_required()
@limiter.limit("3/minute")
def test_llm():
    """测试 LLM 连通性"""
    if not _require_admin():
        return jsonify(code=403, message="权限不足", data=None), 403
    try:
        from app.utils.llm_client import LLMClientManager
        client = LLMClientManager()
        response = client.chat([{"role": "user", "content": "Hello, respond with OK"}])
        return jsonify(code=0, message="LLM 连接正常", data={"response": response[:200] if response else ""})
    except Exception as e:
        return jsonify(code=500, message=f"LLM 连接失败: {str(e)}", data=None), 500


@config_bp.route("/test/wechat", methods=["POST"])
@jwt_required()
@limiter.limit("3/minute")
def test_wechat():
    """测试微信 API 连通性"""
    if not _require_admin():
        return jsonify(code=403, message="权限不足", data=None), 403
    try:
        from app.publisher.wechat_client import WeChatClient
        client = WeChatClient()
        token = client.access_token
        if token:
            return jsonify(code=0, message="微信 API 连接正常", data={"has_token": True})
        return jsonify(code=500, message="获取 Token 失败", data=None), 500
    except Exception as e:
        return jsonify(code=500, message=f"微信连接失败: {str(e)}", data=None), 500


@config_bp.route("/test/image", methods=["POST"])
@jwt_required()
@limiter.limit("3/minute")
def test_image():
    """测试图片生成连通性"""
    if not _require_admin():
        return jsonify(code=403, message="权限不足", data=None), 403
    try:
        from app.config.settings import IMAGE_PROVIDER
        return jsonify(code=0, message=f"当前图片提供商: {IMAGE_PROVIDER}", data={"provider": IMAGE_PROVIDER})
    except Exception as e:
        return jsonify(code=500, message=f"检查失败: {str(e)}", data=None), 500
