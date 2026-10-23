from sqlalchemy import Column, DateTime, Float, Integer, String, Text, Index

from database.database import Base
from app.timezone import now_ist_naive


class DetectionJob(Base):
    __tablename__ = "detection_jobs"

    id = Column(Integer, primary_key=True, index=True)
    ip = Column(String(45), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="pending", index=True)
    result_status = Column(String(10), nullable=True)
    latency_ms = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=now_ist_naive)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=now_ist_naive,
        onupdate=now_ist_naive,
    )

    __table_args__ = (
        Index("ix_detection_jobs_status_created", "status", "created_at"),
    )