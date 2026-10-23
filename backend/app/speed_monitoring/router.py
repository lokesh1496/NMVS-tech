from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import get_current_user
from . import service
from .schema import (
    SpeedTestHistoryItem,
    SpeedTestRequest,
    SpeedTestResponse
)

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