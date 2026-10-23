from datetime import datetime
from app.timezone import IndiaTimeModel
from pydantic import ConfigDict


class MonitoringResponse(IndiaTimeModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ip: str
    status: str
    checked_at: datetime