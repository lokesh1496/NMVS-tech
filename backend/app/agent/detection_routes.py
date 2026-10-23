import ipaddress
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, IPvAnyAddress
from sqlalchemy.exc import SQLAlchemyError

from app.dependencies import get_current_user
from app.agent.detection_model import DetectionJob
from database.database import SessionLocal
from app.timezone import now_ist_naive

router = APIRouter(
    prefix="/devices/detection-requests",
    tags=["Device Detection"],
    dependencies=[Depends(get_current_user)],
)


class DetectionRequest(BaseModel):
    ip: IPvAnyAddress


@router.post("", status_code=201)
def create_detection_job(payload: DetectionRequest):
    ip = str(ipaddress.ip_address(str(payload.ip)))

    db = SessionLocal()
    try:
        # Avoid creating many simultaneous jobs for the same IP.
        existing = (
            db.query(DetectionJob)
            .filter(
                DetectionJob.ip == ip,
                DetectionJob.status.in_(["pending", "running"]),
            )
            .order_by(DetectionJob.id.desc())
            .first()
        )

        if existing:
            return {
                "job_id": existing.id,
                "ip": existing.ip,
                "status": existing.status,
            }

        job = DetectionJob(ip=ip, status="pending")
        db.add(job)
        db.commit()
        db.refresh(job)

        return {
            "job_id": job.id,
            "ip": job.ip,
            "status": job.status,
        }
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not queue device detection",
        ) from exc
    finally:
        db.close()


@router.get("/{job_id}")
def get_detection_job(job_id: int):
    db = SessionLocal()
    try:
        job = db.query(DetectionJob).filter(
            DetectionJob.id == job_id
        ).first()

        if job is None:
            raise HTTPException(status_code=404, detail="Detection job not found")

        # Do not leave jobs pending/running forever if the agent is offline.
        now = now_ist_naive()
        age = now - job.created_at

        if job.status in ("pending", "running") and age > timedelta(seconds=30):
            job.status = "timeout"
            job.error_message = "Local Agent did not respond in time"
            job.updated_at = now
            db.commit()

        return {
            "job_id": job.id,
            "ip": job.ip,
            "status": job.status,
            "result_status": job.result_status,
            "latency_ms": job.latency_ms,
            "error_message": job.error_message,
            "created_at": job.created_at.isoformat(),
            "updated_at": job.updated_at.isoformat(),
        }
    finally:
        db.close()