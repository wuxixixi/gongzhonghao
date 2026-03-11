"""任务历史模型"""

from datetime import datetime, timezone

from web.extensions import db


class TaskHistory(db.Model):
    __tablename__ = "task_histories"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    task_type = db.Column(db.String(50), nullable=False, index=True)  # daily_hot / deep_analysis
    status = db.Column(db.String(20), nullable=False, default="pending", index=True)
    triggered_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    started_at = db.Column(db.DateTime, nullable=True)
    finished_at = db.Column(db.DateTime, nullable=True)
    duration_seconds = db.Column(db.Float, nullable=True)
    report_json = db.Column(db.Text, nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    article_date = db.Column(db.String(6), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    triggerer = db.relationship("User", foreign_keys=[triggered_by], lazy="select")

    def to_dict(self):
        import json
        report = None
        if self.report_json:
            try:
                report = json.loads(self.report_json)
            except (json.JSONDecodeError, TypeError):
                report = self.report_json
        return {
            "id": self.id,
            "task_type": self.task_type,
            "status": self.status,
            "triggered_by": self.triggered_by,
            "triggered_by_name": self.triggerer.username if self.triggerer else "系统",
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_seconds": self.duration_seconds,
            "report": report,
            "error_message": self.error_message,
            "article_date": self.article_date,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
