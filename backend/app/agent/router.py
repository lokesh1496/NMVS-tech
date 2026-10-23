"""Authenticated API endpoints for the NMVS Windows Local Agent.

The agent runs network checks on the LAN and uploads results to this API.
Configure NMVS_AGENT_TOKEN as a high-entropy secret in the backend environment.
"""

import os
import secrets
from ipaddress import ip_address

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field, IPvAnyAddress
from sqlalchemy.exc import SQLAlchemyError

from database.database import SessionLocal
from app.devices.model import Device
from app.monitoring.model import MonitoringHistory
from app.timezone import now_ist_naive

router = APIRouter(prefix="/agent", tags=["Local Agent"])


class AgentResult(BaseModel):
    ip: IPvAnyAddress
    status: str = Field(pattern=r"^(Online|Offline)$")
    latency_ms: float | None = Field(default=None, ge=0, le=600_000)


class AgentResultsBatch(BaseModel):
    results: list[AgentResult] = Field(min_length=1, max_length=500)


def _authenticate_agent(supplied_token: str | None) -> None:
    expected_token = os.getenv("NMVS_AGENT_TOKEN", "").strip()
    if len(expected_token) < 32:
        raise HTTPException(
            status_code=503,
            detail="Local Agent is not configured on the server",
        )
    if not supplied_token or not secrets.compare_digest(supplied_token, expected_token):
        raise HTTPException(status_code=401, detail="Invalid agent token")


@router.get("/devices")
def get_registered_devices(x_agent_token: str | None = Header(default=None)):
    """Return registered device IPs for the authenticated agent to monitor."""
    _authenticate_agent(x_agent_token)
    db = SessionLocal()
    try:
        devices = db.query(Device).order_by(Device.id.asc()).all()
        return {"devices": [{"id": item.id, "name": item.name, "ip": item.ip} for item in devices]}
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail="Could not load registered devices") from exc
    finally:
        db.close()


@router.post("/monitoring-results")
def receive_monitoring_results(
    payload: AgentResultsBatch,
    x_agent_token: str | None = Header(default=None),
):
    """Persist Local Agent results using the existing history and alert systems."""
    _authenticate_agent(x_agent_token)

    # Reject duplicate IP entries in a single batch to avoid duplicate history/alerts.
    normalized_results: dict[str, AgentResult] = {}
    for item in payload.results:
        normalized_ip = str(ip_address(str(item.ip)))
        normalized_results[normalized_ip] = item

    db = SessionLocal()
    transitions: list[tuple[str, str, str | None]] = []
    timestamp = now_ist_naive()
    try:
        for ip, item in normalized_results.items():
            previous = (
                db.query(MonitoringHistory)
                .filter(MonitoringHistory.ip == ip)
                .order_by(MonitoringHistory.checked_at.desc(), MonitoringHistory.id.desc())
                .first()
            )
            old_status = previous.status if previous else None
            history = MonitoringHistory(ip=ip, status=item.status, checked_at=timestamp)
            db.add(history)
            transitions.append((ip, item.status, old_status))
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to save monitoring results") from exc
    finally:
        db.close()

    # Run alert hooks after the history transaction commits. Alert errors should not
    # discard already-persisted monitoring records.
    alert_errors = 0
    for ip, new_status, old_status in transitions:
        try:
            from app.alerts.service import check_and_create_device_status_alert
            check_and_create_device_status_alert(ip, new_status, old_status=old_status)
        except Exception as exc:  # keep processing the remaining results
            alert_errors += 1
            print(f"Local Agent alert hook failed for {ip}: {exc}")

    return {
        "message": "Monitoring results received",
        "received": len(payload.results),
        "history_records_saved": len(transitions),
        "alert_hook_errors": alert_errors,
    }
