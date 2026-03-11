"""认证 API 蓝图"""

from datetime import datetime, timezone

from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    get_jwt,
)

from web.extensions import db, limiter, revoke_token
from web.models.user import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["POST"])
@limiter.limit("5/minute")
def login():
    """用户登录"""
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify(code=400, message="用户名和密码不能为空", data=None), 400

    user = User.query.filter_by(username=username).first()
    if user is None or not user.check_password(password):
        return jsonify(code=401, message="用户名或密码错误", data=None), 401

    if not user.is_active:
        return jsonify(code=403, message="账号已被禁用", data=None), 403

    user.last_login_at = datetime.now(timezone.utc)
    db.session.commit()

    identity = str(user.id)
    additional_claims = {"role": user.role, "username": user.username}
    access_token = create_access_token(identity=identity, additional_claims=additional_claims)
    refresh_token = create_refresh_token(identity=identity, additional_claims=additional_claims)

    return jsonify(code=0, message="登录成功", data={
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": user.to_dict(),
    })


@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    """用户登出"""
    jti = get_jwt()["jti"]
    revoke_token(jti)
    return jsonify(code=0, message="已登出", data=None)


@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    """刷新 Token"""
    identity = get_jwt_identity()
    claims = get_jwt()
    access_token = create_access_token(
        identity=identity,
        additional_claims={"role": claims.get("role"), "username": claims.get("username")},
    )
    return jsonify(code=0, message="ok", data={"access_token": access_token})


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    """获取当前用户信息"""
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if user is None:
        return jsonify(code=404, message="用户不存在", data=None), 404
    return jsonify(code=0, message="ok", data=user.to_dict())


@auth_bp.route("/me", methods=["PUT"])
@jwt_required()
def update_me():
    """更新当前用户信息"""
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if user is None:
        return jsonify(code=404, message="用户不存在", data=None), 404

    data = request.get_json(silent=True) or {}
    if "password" in data:
        pw = data["password"]
        if len(pw) < 8:
            return jsonify(code=400, message="密码长度至少8位", data=None), 400
        user.set_password(pw)
    db.session.commit()
    return jsonify(code=0, message="更新成功", data=user.to_dict())


def _require_admin():
    """检查是否管理员"""
    claims = get_jwt()
    return claims.get("role") == "admin"


@auth_bp.route("/users", methods=["GET"])
@jwt_required()
def list_users():
    """用户列表 (仅管理员)"""
    if not _require_admin():
        return jsonify(code=403, message="权限不足", data=None), 403
    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify(code=0, message="ok", data=[u.to_dict() for u in users])


@auth_bp.route("/users", methods=["POST"])
@jwt_required()
def create_user():
    """创建用户 (仅管理员)"""
    if not _require_admin():
        return jsonify(code=403, message="权限不足", data=None), 403

    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    role = data.get("role", "editor")

    if not username or not password:
        return jsonify(code=400, message="用户名和密码不能为空", data=None), 400
    if len(password) < 8:
        return jsonify(code=400, message="密码长度至少8位", data=None), 400
    if role not in ("admin", "editor"):
        return jsonify(code=400, message="角色必须为 admin 或 editor", data=None), 400
    if User.query.filter_by(username=username).first():
        return jsonify(code=400, message="用户名已存在", data=None), 400

    user = User(username=username, role=role, is_active=True)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return jsonify(code=0, message="创建成功", data=user.to_dict())


@auth_bp.route("/users/<int:user_id>", methods=["PUT"])
@jwt_required()
def update_user(user_id):
    """更新用户 (仅管理员)"""
    if not _require_admin():
        return jsonify(code=403, message="权限不足", data=None), 403

    user = db.session.get(User, user_id)
    if user is None:
        return jsonify(code=404, message="用户不存在", data=None), 404

    data = request.get_json(silent=True) or {}
    if "role" in data and data["role"] in ("admin", "editor"):
        user.role = data["role"]
    if "is_active" in data:
        user.is_active = bool(data["is_active"])
    if "password" in data and len(data["password"]) >= 8:
        user.set_password(data["password"])
    db.session.commit()
    return jsonify(code=0, message="更新成功", data=user.to_dict())


@auth_bp.route("/users/<int:user_id>", methods=["DELETE"])
@jwt_required()
def delete_user(user_id):
    """删除用户 (仅管理员)"""
    if not _require_admin():
        return jsonify(code=403, message="权限不足", data=None), 403

    current_user_id = int(get_jwt_identity())
    if user_id == current_user_id:
        return jsonify(code=400, message="不能删除自己", data=None), 400

    user = db.session.get(User, user_id)
    if user is None:
        return jsonify(code=404, message="用户不存在", data=None), 404

    db.session.delete(user)
    db.session.commit()
    return jsonify(code=0, message="删除成功", data=None)
