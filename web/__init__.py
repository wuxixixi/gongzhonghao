"""Flask Web 管理界面 - App Factory"""

import os
from pathlib import Path
from flask import Flask
from flask_cors import CORS

from web.extensions import db, jwt, migrate, limiter
from web.config import config_map


def create_app(config_name: str = None) -> Flask:
    """创建 Flask 应用实例"""
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development")

    app = Flask(
        __name__,
        instance_path=str(Path(__file__).resolve().parent.parent / "instance"),
        static_folder=str(
            Path(__file__).resolve().parent / "frontend" / "dist"
        ),
        static_url_path="",
    )

    # 加载配置
    app.config.from_object(config_map.get(config_name, config_map["development"]))

    # 初始化扩展
    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})

    # 注册蓝图
    _register_blueprints(app)

    # 注册错误处理
    _register_error_handlers(app)

    # 创建数据库表 & 初始化默认数据
    with app.app_context():
        import web.models  # noqa: F401 确保模型被导入
        db.create_all()
        _init_default_data(app)

    # SPA fallback: 非 /api 路由返回 index.html
    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_spa(path):
        from flask import send_from_directory

        static_dir = app.static_folder
        file_path = os.path.join(static_dir, path)
        if path and os.path.isfile(file_path):
            return send_from_directory(static_dir, path)
        index_path = os.path.join(static_dir, "index.html")
        if os.path.isfile(index_path):
            return send_from_directory(static_dir, "index.html")
        return {"code": 404, "message": "前端未构建，请先运行 npm run build"}, 404

    return app


def _register_blueprints(app: Flask):
    """注册所有 API 蓝图"""
    from web.api.auth import auth_bp
    from web.api.config_api import config_bp
    from web.api.content import content_bp
    from web.api.monitor import monitor_bp
    from web.api.publish import publish_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(config_bp, url_prefix="/api/config")
    app.register_blueprint(content_bp, url_prefix="/api/content")
    app.register_blueprint(monitor_bp, url_prefix="/api/monitor")
    app.register_blueprint(publish_bp, url_prefix="/api/publish")


def _register_error_handlers(app: Flask):
    """注册全局错误处理器"""

    @app.errorhandler(400)
    def bad_request(e):
        return {"code": 400, "message": str(e.description), "data": None}, 400

    @app.errorhandler(401)
    def unauthorized(e):
        return {"code": 401, "message": "未授权，请先登录", "data": None}, 401

    @app.errorhandler(403)
    def forbidden(e):
        return {"code": 403, "message": "权限不足", "data": None}, 403

    @app.errorhandler(404)
    def not_found(e):
        return {"code": 404, "message": "资源不存在", "data": None}, 404

    @app.errorhandler(429)
    def rate_limited(e):
        return {"code": 429, "message": "请求过于频繁，请稍后重试", "data": None}, 429

    @app.errorhandler(500)
    def internal_error(e):
        return {"code": 500, "message": "服务器内部错误", "data": None}, 500


def _init_default_data(app: Flask):
    """初始化默认管理员账户"""
    from web.models.user import User

    if User.query.filter_by(username="admin").first() is None:
        default_pw = os.getenv("ADMIN_DEFAULT_PASSWORD", "admin123456")
        admin = User(username="admin", role="admin", is_active=True)
        admin.set_password(default_pw)
        db.session.add(admin)
        db.session.commit()
