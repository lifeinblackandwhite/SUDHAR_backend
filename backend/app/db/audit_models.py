from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from app.db.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    issue_id = Column(Integer, ForeignKey("issues.id", ondelete="CASCADE"), nullable=False)

    actor_type = Column(String, nullable=False)   # system / citizen / community / official
    actor_id = Column(String, nullable=True)

    action = Column(String, nullable=False)       # AUTO_REJECTED, STATE_CHANGED, etc.

    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    extra = Column(JSON, nullable=True)

    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
