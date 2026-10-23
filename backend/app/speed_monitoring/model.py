from sqlalchemy import Column, DateTime, Float, Integer, String
from app.timezone import as_ist, now_ist_naive
from database.database import Base


class DeviceBandwidthHistory(Base):
    __tablename__ = "device_bandwidth_history"

    id = Column(Integer, primary_key=True, index=True)
    ip = Column(String, nullable=False, index=True)
    download_mbps = Column(Float, nullable=True)
    upload_mbps = Column(Float, nullable=True)
    ping_ms = Column(Float, nullable=True)
    tested_at = Column(
        DateTime,
        default=now_ist_naive,
        nullable=False
    )

    def to_dict(self):
        return {
            "id": self.id,
            "ip": self.ip,
            "download_mbps": self.download_mbps,
            "upload_mbps": self.upload_mbps,
            "ping_ms": self.ping_ms,
            "tested_at": as_ist(self.tested_at).isoformat()
        }


SpeedTestHistory = DeviceBandwidthHistory