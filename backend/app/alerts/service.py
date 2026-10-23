from database.database import SessionLocal
from app.devices import crud as device_crud
from . import crud
from .model import Alert
from .schema import AlertsSummary


def get_alerts(
    status: str | None = None,
    severity: str | None = None,
    alert_type: str | None = None,
    limit: int = 50
) -> list[Alert]:
    """Retrieve list of alerts with optional status, severity, and alert_type filters."""
    db = SessionLocal()
    try:
        return crud.get_alerts(
            db,
            status=status,
            severity=severity,
            alert_type=alert_type,
            limit=limit
        )
    finally:
        db.close()


def get_alert_by_id(alert_id: int) -> Alert | None:
    """Retrieve a single alert by ID."""
    db = SessionLocal()
    try:
        return crud.get_alert_by_id(db, alert_id)
    finally:
        db.close()


def create_alert(
    device_ip: str,
    message: str,
    title: str | None = None,
    device_id: int | None = None,
    device_name: str | None = None,
    alert_type: str = "DISCONNECTED",
    severity: str = "critical"
) -> Alert:
    """Manually or programmatically create an alert."""
    db = SessionLocal()
    try:
        if not device_id or not device_name:
            dev = device_crud.get_device_by_ip(device_ip.strip())
            if dev:
                device_id = device_id or dev.id
                device_name = device_name or dev.name

        return crud.create_alert(
            db=db,
            device_ip=device_ip.strip(),
            message=message.strip(),
            title=title,
            device_id=device_id,
            device_name=device_name,
            alert_type=alert_type,
            severity=severity,
            status="active"
        )
    finally:
        db.close()


def acknowledge_alert(alert_id: int) -> Alert | None:
    """Mark an alert as acknowledged."""
    db = SessionLocal()
    try:
        return crud.update_alert_status(db, alert_id, "acknowledged")
    finally:
        db.close()


def resolve_alert(alert_id: int) -> Alert | None:
    """Mark an alert as resolved."""
    db = SessionLocal()
    try:
        return crud.update_alert_status(db, alert_id, "resolved")
    finally:
        db.close()


def delete_alert(alert_id: int) -> bool:
    """Delete an alert by ID."""
    db = SessionLocal()
    try:
        return crud.delete_alert(db, alert_id)
    finally:
        db.close()


def get_summary() -> AlertsSummary:
    """Return counts of total, active, disconnected, connected, critical, warning, and resolved alerts."""
    db = SessionLocal()
    try:
        return crud.get_alerts_summary(db)
    finally:
        db.close()


def check_and_create_device_status_alert(ip: str, new_status: str, old_status: str | None = None):
    """
    Hook called during device monitoring:
    - If device went Offline: triggers a DISCONNECTED alert.
    - If device recovered to Online: resolves active DISCONNECTED alerts and logs a CONNECTED alert.
    """
    db = SessionLocal()
    try:
        dev = device_crud.get_device_by_ip(ip)
        dev_name = dev.name if dev else ip
        dev_id = dev.id if dev else None

        if new_status == "Offline":
            # Check if active DISCONNECTED alert already exists for this IP to prevent duplicate spam
            existing_active = (
                db.query(Alert)
                .filter(
                    Alert.device_ip == ip,
                    Alert.status == "active",
                    Alert.alert_type == "DISCONNECTED"
                )
                .first()
            )
            if not existing_active:
                crud.create_alert(
                    db=db,
                    device_id=dev_id,
                    device_name=dev_name,
                    device_ip=ip,
                    title=f"Device Disconnected: {dev_name}",
                    alert_type="DISCONNECTED",
                    severity="critical",
                    message=f"Device '{dev_name}' ({ip}) disconnected from the network and is unreachable.",
                    status="active"
                )

        elif new_status == "Online":
            # Resolve any active DISCONNECTED alerts for this IP
            active_disconnects = (
                db.query(Alert)
                .filter(
                    Alert.device_ip == ip,
                    Alert.status == "active",
                    Alert.alert_type == "DISCONNECTED"
                )
                .all()
            )
            had_active_disconnect = len(active_disconnects) > 0
            for a in active_disconnects:
                crud.update_alert_status(db, a.id, "resolved")

            # If it recovered from disconnect or transitioned from Offline, log a CONNECTED alert
            if had_active_disconnect or old_status == "Offline":
                crud.create_alert(
                    db=db,
                    device_id=dev_id,
                    device_name=dev_name,
                    device_ip=ip,
                    title=f"Device Connected: {dev_name}",
                    alert_type="CONNECTED",
                    severity="info",
                    message=f"Device '{dev_name}' ({ip}) reconnected to the network and is responding.",
                    status="resolved"
                )

    finally:
        db.close()
