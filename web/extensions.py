"""Flask 扩展实例"""

from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()
jwt = JWTManager()
migrate = Migrate()
limiter = Limiter(key_func=get_remote_address)

# JWT Token 黑名单 (内存存储，重启后失效)
_revoked_tokens: set = set()


@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    jti = jwt_payload["jti"]
    return jti in _revoked_tokens


def revoke_token(jti: str):
    """将 token 加入黑名单"""
    _revoked_tokens.add(jti)
