from datetime import datetime
from typing import Optional
from app.timezone import IndiaTimeModel
from pydantic import BaseModel, ConfigDict


class SpeedTestRequest(BaseModel):
    ip: str = "internet"


class SpeedTestResponse(BaseModel):
    ip: str = "internet"
    download_mbps: Optional[float] = None
    upload_mbps: Optional[float] = None
    ping_ms: Optional[float] = None
    server: Optional[str] = None
    isp: Optional[str] = None
    client_ip: Optional[str] = None
    error: Optional[str] = None


class SpeedTestHistoryItem(IndiaTimeModel):
    id: int
    ip: str
    download_mbps: Optional[float] = None
    upload_mbps: Optional[float] = None
    ping_ms: Optional[float] = None
    tested_at: datetime

    model_config = ConfigDict(from_attributes=True)