from collections import defaultdict
from datetime import timedelta

from app.timezone import now_ist_naive
from app.devices.model import Device
from app.monitoring.model import MonitoringHistory
from app.speed_monitoring.model import DeviceBandwidthHistory
from database.database import SessionLocal

from .schema import DeviceUptimeMetric, NetworkMetricsSummary


def get_metrics_summary() -> NetworkMetricsSummary:
    """
    Compute aggregate network telemetry metrics: overall uptime percentage,
    average latency, bandwidth averages, and healthy vs degraded device counts.
    """
    db = SessionLocal()
    try:
        devices = db.query(Device).all()
        total_devs = len(devices)

        # 1. Compute Uptime from MonitoringHistory (past 24h)
        cutoff = now_ist_naive() - timedelta(hours=24)
        history_records = (
            db.query(MonitoringHistory)
            .filter(MonitoringHistory.checked_at >= cutoff)
            .all()
        )

        total_checks = len(history_records)
        online_checks = sum(1 for h in history_records if h.status == "Online")
        overall_uptime = (
            round((online_checks / total_checks * 100.0), 1)
            if total_checks > 0
            else None
        )

        # 2. Average Latency & Bandwidth Speeds from speed monitoring history
        recent_speed = (
            db.query(DeviceBandwidthHistory)
            .order_by(DeviceBandwidthHistory.tested_at.desc())
            .limit(10)
            .all()
        )
        avg_lat, avg_dl, avg_ul = None, None, None
        if recent_speed:
            pings = [s.ping_ms for s in recent_speed if s.ping_ms is not None]
            dls = [s.download_mbps for s in recent_speed if s.download_mbps is not None]
            uls = [s.upload_mbps for s in recent_speed if s.upload_mbps is not None]

            if pings:
                avg_lat = round(sum(pings) / len(pings), 1)
            if dls:
                avg_dl = round(sum(dls) / len(dls), 1)
            if uls:
                avg_ul = round(sum(uls) / len(uls), 1)

        # 3. Device health breakdown
        healthy_count = 0
        degraded_count = 0
        unmonitored_count = 0
        records_by_ip = defaultdict(list)
        for record in history_records:
            records_by_ip[record.ip].append(record)
        for dev in devices:
            dev_checks = records_by_ip[dev.ip]
            if not dev_checks:
                unmonitored_count += 1
            else:
                up_pct = sum(1 for c in dev_checks if c.status == "Online") / len(dev_checks)
                if up_pct >= 0.9:
                    healthy_count += 1
                else:
                    degraded_count += 1

        return NetworkMetricsSummary(
            overall_network_uptime=overall_uptime,
            average_latency_ms=avg_lat,
            average_download_mbps=avg_dl,
            average_upload_mbps=avg_ul,
            total_devices_evaluated=total_devs,
            healthy_devices_count=healthy_count,
            degraded_devices_count=degraded_count,
            unmonitored_devices_count=unmonitored_count,
        )
    finally:
        db.close()


def get_devices_uptime(hours: int = 24) -> list[DeviceUptimeMetric]:
    """
    Calculate availability and uptime percentage for each registered device over the specified time window.
    """
    db = SessionLocal()
    try:
        devices = db.query(Device).all()
        cutoff = now_ist_naive() - timedelta(hours=hours)

        records = (
            db.query(MonitoringHistory)
            .filter(MonitoringHistory.checked_at >= cutoff)
            .order_by(MonitoringHistory.checked_at.desc(), MonitoringHistory.id.desc())
            .all()
        )

        latest_status = {}
        for record in records:
            latest_status.setdefault(record.ip, record.status)

        results = []
        for dev in devices:
            dev_records = [r for r in records if r.ip == dev.ip]
            total = len(dev_records)
            online = sum(1 for r in dev_records if r.status == "Online")
            offline = total - online

            latest = latest_status.get(dev.ip, "Unknown")
            uptime_pct = round((online / total * 100.0), 1) if total > 0 else None

            results.append(
                DeviceUptimeMetric(
                    device_ip=dev.ip,
                    device_name=dev.name,
                    device_type=dev.device_type,
                    total_checks=total,
                    online_checks=online,
                    offline_checks=offline,
                    uptime_percentage=uptime_pct,
                    current_status=latest
                )
            )

        return sorted(results, key=lambda x: x.uptime_percentage, reverse=True)
    finally:
        db.close()
