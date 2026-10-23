
"""Authenticated API endpoints for the NMVS Windows Local Agent.

The agent runs network checks on the LAN, uploads monitoring results,
and processes on-demand detection jobs for arbitrary IP addresses.

Configure NMVS_AGENT_TOKEN as a high-entropy secret in the backend environment.
"""

import os
import secrets
from ipaddress import ip_address

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field, IPvAnyAddress
from sqlalchemy.exc import SQLAlchemyError

from app.agent.detection_model import DetectionJob
from app.devices.model import Device
from app.monitoring.model import MonitoringHistory
from app.speed_monitoring.model import DeviceBandwidthHistory
from app.speed_monitoring.speed_job_model import SpeedTestJob
from app.timezone import now_ist_naive
from database.database import SessionLocal


router = APIRouter(prefix="/agent", tags=["Local Agent"])


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class AgentResult(BaseModel):
    ip: IPvAnyAddress
    status: str = Field(pattern=r"^(Online|Offline)$")
    latency_ms: float | None = Field(default=None, ge=0, le=600_000)


class AgentResultsBatch(BaseModel):
    results: list[AgentResult] = Field(min_length=1, max_length=500)


class AgentDetectionRequest(BaseModel):
    ip: IPvAnyAddress


class AgentDetectionResult(BaseModel):
    status: str = Field(pattern=r"^(Online|Offline)$")
    latency_ms: float | None = Field(default=None, ge=0, le=600_000)


class AgentSpeedTestResult(BaseModel):
    status: str = Field(pattern=r"^(completed|failed)$")
    download_mbps: float | None = Field(default=None, ge=0, le=100_000)
    upload_mbps: float | None = Field(default=None, ge=0, le=100_000)
    ping_ms: float | None = Field(default=None, ge=0, le=600_000)
    error_message: str | None = Field(default=None, max_length=1000)


# ---------------------------------------------------------------------------
# Agent authentication
# ---------------------------------------------------------------------------

def _authenticate_agent(supplied_token: str | None) -> None:
    expected_token = os.getenv("NMVS_AGENT_TOKEN", "").strip()

    if len(expected_token) < 32:
        raise HTTPException(
            status_code=503,
            detail="Local Agent is not configured on the server",
        )

    if not supplied_token or not secrets.compare_digest(
        supplied_token, expected_token
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid agent token",
        )


# ---------------------------------------------------------------------------
# Existing monitoring endpoints
# ---------------------------------------------------------------------------

@router.get("/devices")
def get_registered_devices(
    x_agent_token: str | None = Header(default=None),
):
    """Return registered device IPs for the authenticated agent to monitor."""
    _authenticate_agent(x_agent_token)

    db = SessionLocal()
    try:
        devices = db.query(Device).order_by(Device.id.asc()).all()

        return {
            "devices": [
                {
                    "id": item.id,
                    "name": item.name,
                    "ip": item.ip,
                }
                for item in devices
            ]
        }

    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not load registered devices",
        ) from exc

    finally:
        db.close()


@router.post("/monitoring-results")
def receive_monitoring_results(
    payload: AgentResultsBatch,
    x_agent_token: str | None = Header(default=None),
):
    """Persist Local Agent monitoring results and trigger status alerts."""
    _authenticate_agent(x_agent_token)

    # Normalize IP addresses and avoid duplicate entries in a batch.
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
                .order_by(
                    MonitoringHistory.checked_at.desc(),
                    MonitoringHistory.id.desc(),
                )
                .first()
            )

            old_status = previous.status if previous else None

            # Update current status only when the device is registered.
            device = db.query(Device).filter(Device.ip == ip).first()

            if device:
                device.status = item.status

            # Persist history for registered and unregistered IPs.
            history = MonitoringHistory(
                ip=ip,
                status=item.status,
                checked_at=timestamp,
            )
            db.add(history)

            transitions.append((ip, item.status, old_status))

        db.commit()

    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to save monitoring results",
        ) from exc

    finally:
        db.close()

    # Run alert hooks after committing the monitoring transaction.
    alert_errors = 0

    for ip, new_status, old_status in transitions:
        try:
            from app.alerts.service import check_and_create_device_status_alert

            check_and_create_device_status_alert(
                ip,
                new_status,
                old_status=old_status,
            )

        except Exception as exc:
            alert_errors += 1
            print(f"Local Agent alert hook failed for {ip}: {exc}")

    return {
        "message": "Monitoring results received",
        "received": len(payload.results),
        "history_records_saved": len(transitions),
        "alert_hook_errors": alert_errors,
    }


# ---------------------------------------------------------------------------
# Existing registered-device detection endpoint
# ---------------------------------------------------------------------------

@router.post("/detect")
def detect_device_from_agent(
    payload: AgentDetectionRequest,
    x_agent_token: str | None = Header(default=None),
):
    """Return the latest monitoring result for a registered device."""
    _authenticate_agent(x_agent_token)

    ip = str(ip_address(str(payload.ip)))

    db = SessionLocal()
    try:
        device = (
            db.query(Device)
            .filter(Device.ip == ip)
            .first()
        )

        if device is None:
            raise HTTPException(
                status_code=404,
                detail="Device is not registered",
            )

        latest = (
            db.query(MonitoringHistory)
            .filter(MonitoringHistory.ip == ip)
            .order_by(
                MonitoringHistory.checked_at.desc(),
                MonitoringHistory.id.desc(),
            )
            .first()
        )

        return {
            "ip": ip,
            "status": latest.status if latest else device.status,
            "source": "local_agent",
        }

    finally:
        db.close()


# ---------------------------------------------------------------------------
# On-demand detection queue: agent claims the next pending job
# ---------------------------------------------------------------------------

@router.get("/detection-requests/next")
def get_next_detection_request(
    x_agent_token: str | None = Header(default=None),
):
    """Claim the next queued IP detection job for the Local Agent."""
    _authenticate_agent(x_agent_token)

    db = SessionLocal()

    try:
        query = (
            db.query(DetectionJob)
            .filter(DetectionJob.status == "pending")
            .order_by(
                DetectionJob.created_at.asc(),
                DetectionJob.id.asc(),
            )
        )

        # PostgreSQL row locking prevents concurrent agents from claiming
        # the same pending job at the same time.
        if db.bind and db.bind.dialect.name == "postgresql":
            query = query.with_for_update(skip_locked=True)

        job = query.first()

        if job is None:
            return {"job": None}

        job.status = "running"
        job.updated_at = now_ist_naive()

        db.commit()

        return {
            "job": {
                "job_id": job.id,
                "ip": job.ip,
            }
        }

    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not claim detection request",
        ) from exc

    finally:
        db.close()


# ---------------------------------------------------------------------------
# On-demand detection queue: agent submits the ping result
# ---------------------------------------------------------------------------

@router.post("/detection-requests/{job_id}/result")
def submit_detection_result(
    job_id: int,
    payload: AgentDetectionResult,
    x_agent_token: str | None = Header(default=None),
):
    """Save the result of a Local Agent on-demand IP ping."""
    _authenticate_agent(x_agent_token)

    db = SessionLocal()

    try:
        query = (
            db.query(DetectionJob)
            .filter(DetectionJob.id == job_id)
        )

        if db.bind and db.bind.dialect.name == "postgresql":
            query = query.with_for_update()

        job = query.first()

        if job is None:
            raise HTTPException(
                status_code=404,
                detail="Detection job not found",
            )

        if job.status != "running":
            raise HTTPException(
                status_code=409,
                detail=f"Detection job is not running: {job.status}",
            )

        job.result_status = payload.status
        job.latency_ms = payload.latency_ms
        job.status = "completed"
        job.updated_at = now_ist_naive()

        db.commit()

        return {
            "message": "Detection result saved",
            "job_id": job.id,
            "ip": job.ip,
            "status": job.status,
            "result_status": job.result_status,
            "latency_ms": job.latency_ms,
        }

    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not save detection result",
        ) from exc

    finally:
        db.close()


@router.get("/speed-tests/next")
def get_next_speed_test(
    x_agent_token: str | None = Header(default=None),
):
    """Claim the next queued speed test for the Local Agent."""
    _authenticate_agent(x_agent_token)

    db = SessionLocal()
    try:
        query = (
            db.query(SpeedTestJob)
            .filter(SpeedTestJob.status == "pending")
            .order_by(SpeedTestJob.created_at.asc(), SpeedTestJob.id.asc())
        )

        if db.bind and db.bind.dialect.name == "postgresql":
            query = query.with_for_update(skip_locked=True)

        job = query.first()
        if job is None:
            return {"job": None}

        job.status = "running"
        job.updated_at = now_ist_naive()
        db.commit()

        return {"job": {"job_id": job.id, "ip": job.ip}}
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not claim speed test",
        ) from exc
    finally:
        db.close()


@router.post("/speed-tests/{job_id}/result")
def submit_speed_test_result(
    job_id: int,
    payload: AgentSpeedTestResult,
    x_agent_token: str | None = Header(default=None),
):
    """Persist a Local Agent speed test result and add successful tests to history."""
    _authenticate_agent(x_agent_token)

    db = SessionLocal()
    try:
        query = db.query(SpeedTestJob).filter(SpeedTestJob.id == job_id)
        if db.bind and db.bind.dialect.name == "postgresql":
            query = query.with_for_update()
        job = query.first()

        if job is None:
            raise HTTPException(status_code=404, detail="Speed test not found")
        if job.status != "running":
            raise HTTPException(
                status_code=409,
                detail=f"Speed test is not running: {job.status}",
            )

        if payload.status == "completed":
            if (
                payload.download_mbps is None
                or payload.upload_mbps is None
                or payload.ping_ms is None
            ):
                raise HTTPException(
                    status_code=422,
                    detail="Completed speed tests must include all measurements",
                )

            record = DeviceBandwidthHistory(
                ip=job.ip,
                download_mbps=payload.download_mbps,
                upload_mbps=payload.upload_mbps,
                ping_ms=payload.ping_ms,
            )
            db.add(record)
            job.download_mbps = payload.download_mbps
            job.upload_mbps = payload.upload_mbps
            job.ping_ms = payload.ping_ms
            job.status = "completed"
        else:
            job.status = "failed"

        job.error_message = payload.error_message
        job.updated_at = now_ist_naive()
        db.commit()

        return {
            "job_id": job.id,
            "ip": job.ip,
            "status": job.status,
            "download_mbps": job.download_mbps,
            "upload_mbps": job.upload_mbps,
            "ping_ms": job.ping_ms,
            "error_message": job.error_message,
        }
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not save speed test result",
        ) from exc
    finally:
        db.close()
