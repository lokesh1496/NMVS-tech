from app.timezone import now_ist_naive
from database.database import SessionLocal
from app.devices.model import Device
from .model import MonitoringHistory
from .monitor import check_device_status


def get_device_status(ip: str):
    """
    Check the current status of one device.
    """
    return check_device_status(ip)


def check_and_save_device(ip: str):
    """
    Check device status immediately, update Device table if present,
    and save entry in MonitoringHistory.
    """
    db = SessionLocal()
    try:
        result = check_device_status(ip)
        status = result.get("status", "Offline")

        device = (
            db.query(Device)
            .filter(Device.ip == ip)
            .first()
        )
        if device:
            device.status = status

        history = MonitoringHistory(
            ip=ip,
            status=status,
            checked_at=now_ist_naive()
        )
        db.add(history)
        db.commit()
        db.refresh(history)

        return history
    finally:
        db.close()


def update_dynamic_status(ip: str, new_status: str):
    """
    Update the current status of one device in the database.
    """
    db = SessionLocal()
    try:
        device = (
            db.query(Device)
            .filter(Device.ip == ip)
            .first()
        )

        if device:
            device.status = new_status
            db.commit()

        return device

    finally:
        db.close()


def update_device_status_from_monitor():
    """
    Check every device stored in the database
    and update its current status.
    """
    db = SessionLocal()

    try:
        devices = db.query(Device).all()

        results = []

        for device in devices:

            result = check_device_status(device.ip)

            new_status = result.get(
                "status",
                "Unknown"
            )

            device.status = new_status

            results.append({
                "ip": device.ip,
                "status": new_status
            })

        db.commit()

        return results

    finally:
        db.close()


def get_monitoring_history(ip: str, limit: int = 20):
    """
    Get monitoring history for a specific IP.
    """
    db = SessionLocal()
    try:
        return (
            db.query(MonitoringHistory)
            .filter(MonitoringHistory.ip == ip)
            .order_by(MonitoringHistory.checked_at.desc())
            .limit(limit)
            .all()
        )
    finally:
        db.close()


def get_all_monitoring_history(limit: int = 100):
    """
    Get monitoring history across all devices.
    """
    db = SessionLocal()
    try:
        return (
            db.query(MonitoringHistory)
            .order_by(MonitoringHistory.checked_at.desc())
            .limit(limit)
            .all()
        )
    finally:
        db.close()