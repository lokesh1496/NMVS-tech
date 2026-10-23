from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_current_user
from . import service
from .schema import MonitoringResponse


router = APIRouter(
    prefix="/monitoring",
    tags=["Monitoring"],
    dependencies=[Depends(get_current_user)],
)


# =========================================================
# CHECK DEVICE NOW
# =========================================================

@router.get(
    "/check/{ip}",
    response_model=MonitoringResponse
)
def check_device(ip: str):

    result = service.check_and_save_device(ip)

    if result is None:
        raise HTTPException(
            status_code=400,
            detail="Unable to monitor device"
        )

    return result


# =========================================================
# GET MONITORING HISTORY
# =========================================================

@router.get(
    "/history/{ip}",
    response_model=list[MonitoringResponse]
)
def get_monitoring_history(
    ip: str,
    limit: int = 20
):

    history = service.get_monitoring_history(
        ip,
        limit
    )

    return history


# =========================================================
# GET ALL MONITORING HISTORY
# =========================================================

@router.get(
    "/history",
    response_model=list[MonitoringResponse]
)
def get_all_monitoring_history(
    limit: int = 100
):

    return service.get_all_monitoring_history(
        limit
    )