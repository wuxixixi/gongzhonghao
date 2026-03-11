"""系统配置模型"""

from datetime import datetime, timezone

from web.extensions import db


class SystemConfig(db.Model):
    __tablename__ = "system_configs"
    __table_args__ = (db.UniqueConstraint("category", "key", name="uq_category_key"),)

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    category = db.Column(db.String(50), nullable=False, index=True)
    key = db.Column(db.String(100), nullable=False)
    value = db.Column(db.Text, default="")
    value_type = db.Column(db.String(20), default="string")  # string / int / bool
    is_secret = db.Column(db.Boolean, default=False)
    description = db.Column(db.Text, default="")
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self, mask_secret=True):
        val = self.value
        if mask_secret and self.is_secret and val:
            if len(val) > 8:
                val = val[:3] + "****" + val[-4:]
            else:
                val = "****"
        return {
            "id": self.id,
            "category": self.category,
            "key": self.key,
            "value": val,
            "value_type": self.value_type,
            "is_secret": self.is_secret,
            "description": self.description,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
