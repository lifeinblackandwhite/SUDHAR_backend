from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from geoalchemy2 import Geography
from .database import Base

class Issue(Base):
    __tablename__ = "issues"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=True)   # firebase uid later
    description = Column(Text, nullable=False)
    category = Column(String, nullable=False)

    state = Column(String)
    city = Column(String)
    area = Column(String)
    pincode = Column(String)

    location = Column(Geography(geometry_type="POINT", srid=4326))

    status = Column(String, default="Pending Verification")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class IssueMedia(Base):
    __tablename__ = "issue_media"

    id = Column(Integer, primary_key=True, index=True)
    issue_id = Column(Integer, ForeignKey("issues.id", ondelete="CASCADE"))
    file_path = Column(String, nullable=False)
