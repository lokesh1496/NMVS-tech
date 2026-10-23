from sqlalchemy import Column, DateTime, Float, Index, Integer, String, Text

from app.timezone import now_ist_naive
from database.database import Base


class SpeedTestJob(Base):
    __tablename__ = "speed_test_jobs"

    id = Column(Integer, primary_key=True, index=True)
    ip = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False, default="pending", index=True)
    download_mbps = Column(Float, nullable=True)
    upload_mbps = Column(Float, nullable=True)
    ping_ms = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=now_ist_naive)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=now_ist_naive,
        onupdate=now_ist_naive,
    )

    __table_args__ = (
        Index("ix_speed_test_jobs_status_created", "status", "created_at"),
    )
