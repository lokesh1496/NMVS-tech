from sqlalchemy import Column, DateTime, Integer, String

from app.timezone import now_ist_naive
from database.database import Base


class MonitoringHistory(Base):
    __tablename__ = "monitoring_history"

    id = Column(Integer, primary_key=True, index=True)
    ip = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False)
    checked_at = Column(
        DateTime,
        default=now_ist_naive,
        nullable=False
    )