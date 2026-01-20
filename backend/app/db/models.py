from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Boolean, Float
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from geoalchemy2 import Geography
from .database import Base
from app.db.audit_models import AuditLog


class Issue(Base):
    __tablename__ = "issues"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=True)   # firebase uid later
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String, nullable=False)

    state = Column(String)
    city = Column(String)
    area = Column(String)
    pincode = Column(String)

    location = Column(Geography(geometry_type="POINT", srid=4326))

    status = Column(String, default="SUBMITTED", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    abuse_cleared = Column(Boolean, default=False, nullable=False)
    
    # Priority score calculated by dynamic ranking service
    priority_score = Column(Float, default=0.0, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())



class IssueMedia(Base):
    __tablename__ = "issue_media"

    id = Column(Integer, primary_key=True, index=True)
    issue_id = Column(Integer, ForeignKey("issues.id", ondelete="CASCADE"))
    file_path = Column(String, nullable=False)

class IssueEvent(Base):
    __tablename__ = "issue_events"

    id = Column(Integer, primary_key=True, index=True)

    issue_id = Column(Integer, ForeignKey("issues.id", ondelete="CASCADE"), nullable=False)

    actor_type = Column(String, nullable=False)
    # citizen | official | admin | system

    actor_id = Column(String, nullable=True)
    # firebase uid / official id / null for system

    action = Column(String, nullable=False)
    # ISSUE_CREATED, STATUS_CHANGED, IMAGE_UPLOADED, ASSIGNED, etc.

    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)

    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

class IssueVerification(Base):
    __tablename__ = "issue_verifications"

    id = Column(Integer, primary_key=True)
    issue_id = Column(Integer, ForeignKey("issues.id", ondelete="CASCADE"))
    verifier_id = Column(String, nullable=False)  # firebase UID
    vote = Column(String, nullable=True)  # CONFIRM | DENY - set later after evaluation
    description = Column(Text, nullable=True)
    image_path = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class GovtOfficial(Base):
    __tablename__ = "GOVTOFFICIALS"

    sso = Column(String, primary_key=True, index=True)  # Single Sign-On ID

    name = Column(String, nullable=False)
    department = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)

    state = Column(String, nullable=False)
    city = Column(String, nullable=False)

    category = Column(String, nullable=False)
    # e.g. sanitation, roads, electricity, water, etc.