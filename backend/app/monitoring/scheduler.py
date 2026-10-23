import asyncio

from app.timezone import now_ist_naive
from database.database import SessionLocal
from app.monitoring.model import MonitoringHistory
from app.monitoring.service import update_device_status_from_monitor


# scheduler.py — fix the call site
async def monitor_devices(interval: int = 30):
    while True:
        try:
            results = await asyncio.to_thread(update_device_status_from_monitor)

            db = SessionLocal()
            try:
                for result in results:
                    history = MonitoringHistory(
                        ip=result["ip"],
                        status=result["status"],
                        checked_at=now_ist_naive()
                    )
                    db.add(history)
                    print(f"Monitoring {result['ip']}: {result['status']}")

                    try:
                        from app.alerts.service import check_and_create_device_status_alert
                        check_and_create_device_status_alert(result["ip"], result["status"])
                    except Exception as alert_e:
                        print(f"Alert hook notice: {alert_e}")
                db.commit()
            finally:
                db.close()

        except Exception as e:
            print(f"Monitoring error: {e}")

        await asyncio.sleep(interval)

def get_device_history(ip: str, limit: int = 20):
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