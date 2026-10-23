from database.database import SessionLocal
from .model import DeviceBandwidthHistory


def save_result(
    ip: str,
    download_mbps: float = None,
    upload_mbps: float = None,
    ping_ms: float = None
):
    db = SessionLocal()
    try:
        record = DeviceBandwidthHistory(
            ip=ip,
            download_mbps=download_mbps,
            upload_mbps=upload_mbps,
            ping_ms=ping_ms
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record
    finally:
        db.close()


def get_history(limit: int = 20, ip: str = None):
    db = SessionLocal()
    try:
        query = db.query(DeviceBandwidthHistory)
        if ip:
            query = query.filter(DeviceBandwidthHistory.ip == ip)
        return (
            query.order_by(DeviceBandwidthHistory.tested_at.desc())
            .limit(limit)
            .all()
        )
    finally:
        db.close()


def get_history_by_id(history_id: int):
    db = SessionLocal()
    try:
        return (
            db.query(DeviceBandwidthHistory)
            .filter(DeviceBandwidthHistory.id == history_id)
            .first()
        )
    finally:
        db.close()


def delete_history_item(history_id: int):
    db = SessionLocal()
    try:
        record = (
            db.query(DeviceBandwidthHistory)
            .filter(DeviceBandwidthHistory.id == history_id)
            .first()
        )
        if record:
            db.delete(record)
            db.commit()
            return True
        return False
    finally:
        db.close()