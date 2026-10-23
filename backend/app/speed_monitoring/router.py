from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError

from app.speed_monitoring.speed_job_model import SpeedTestJob
from app.timezone import now_ist_naive
from database.database import SessionLocal
from app.dependencies import get_current_user
from . import service
from .schema import (
    SpeedTestHistoryItem,
    SpeedTestRequest,
    SpeedTestResponse
)


class LocalSpeedTestRequest(BaseModel):
    ip: str = Field(default="internet", min_length=1, max_length=255)


router = APIRouter(
    prefix="/speed-monitoring",
    tags=["Speed Monitoring"],
    dependencies=[Depends(get_current_user)],
)


# ==================================================
# 1. RUN SPEED TEST & SAVE TO HISTORY
# ==================================================

@router.post(
    "/run",
    response_model=SpeedTestHistoryItem,
    status_code=status.HTTP_201_CREATED
)
def run_and_save_speed_test(request: SpeedTestRequest = None):
    """
    Run an Internet Speed Test and save the record to history.
    """
    target_ip = request.ip if request else "internet"

    try:
        return service.run_and_save(target_ip)
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Speed test failed: {str(e)}"
        )


@router.post("/local-jobs", status_code=status.HTTP_201_CREATED)
def create_local_speed_test(payload: LocalSpeedTestRequest):
    """Queue an Internet speed test to run from the connected Local Agent."""
    label = payload.ip.strip()
    if not label:
        raise HTTPException(status_code=422, detail="History label cannot be blank")

    db = SessionLocal()
    try:
        job = SpeedTestJob(ip=label, status="pending")
        db.add(job)
        db.commit()
        db.refresh(job)
        return {"job_id": job.id, "ip": job.ip, "status": job.status}
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not queue local speed test",
        ) from exc
    finally:
        db.close()


@router.get("/local-jobs/{job_id}")
def get_local_speed_test(job_id: int):
    db = SessionLocal()
    try:
        job = db.query(SpeedTestJob).filter(SpeedTestJob.id == job_id).first()
        if job is None:
            raise HTTPException(status_code=404, detail="Speed test not found")

        now = now_ist_naive()
        if (
            job.status in ("pending", "running")
            and now - job.created_at > timedelta(seconds=600)
        ):
            job.status = "timeout"
            job.error_message = "Local Agent did not complete the speed test in time"
            job.updated_at = now
            db.commit()

        return {
            "job_id": job.id,
            "ip": job.ip,
            "status": job.status,
            "download_mbps": job.download_mbps,
            "upload_mbps": job.upload_mbps,
            "ping_ms": job.ping_ms,
            "error_message": job.error_message,
            "created_at": job.created_at.isoformat(),
            "updated_at": job.updated_at.isoformat(),
        }
    finally:
        db.close()


# ==================================================
# 2. RUN LIVE SPEED TEST (NO SAVING)
# ==================================================

@router.get(
    "/live",
    response_model=SpeedTestResponse
)
def run_live_speed_test(
    ip: str = Query(default="internet", description="Target IP or 'internet'")
):
    """
    Run a live speed test (download, upload, ping) without saving to database.
    """
    try:
        return service.run_live_test(ip)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Speed test failed: {str(e)}"
        )


# ==================================================
# 3. SPEED TEST HISTORY
# ==================================================

@router.get(
    "/history",
    response_model=list[SpeedTestHistoryItem]
)
def get_speed_test_history(
    limit: int = Query(default=20, ge=1, le=100),
    ip: str = Query(default=None, description="Filter history by target IP")
):
    """
    Retrieve past speed test history records.
    """
    try:
        return service.get_history(limit=limit, ip=ip)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch history: {str(e)}"
        )


@router.get(
    "/history/{history_id}",
    response_model=SpeedTestHistoryItem
)
def get_speed_test_record(history_id: int):
    """
    Retrieve a specific speed test record by ID.
    """
    record = service.get_history_by_id(history_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="History record not found"
        )
    return record


@router.delete(
    "/history/{history_id}"
)
def delete_speed_test_history(history_id: int):
    """
    Delete a specific speed test history record.
    """
    deleted = service.delete_history(history_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="History record not found"
        )
    return {"message": "Speed test history record deleted successfully"}