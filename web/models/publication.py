"""发布记录模型"""

from datetime import datetime, timezone

from web.extensions import db


class PublicationRecord(db.Model):
    __tablename__ = "publication_records"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    article_date = db.Column(db.String(6), nullable=False, index=True)
    article_type = db.Column(db.String(20), nullable=False, default="daily_hot")
    title = db.Column(db.String(200), nullable=True)
    media_id = db.Column(db.String(200), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="draft_created")
    published_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    publisher = db.relationship("User", foreign_keys=[published_by], lazy="select")

    def to_dict(self):
        return {
            "id": self.id,
            "article_date": self.article_date,
            "article_type": self.article_type,
            "title": self.title,
            "media_id": self.media_id,
            "status": self.status,
            "published_by": self.published_by,
            "published_by_name": self.publisher.username if self.publisher else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
