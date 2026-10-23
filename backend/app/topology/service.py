from concurrent.futures import ThreadPoolExecutor

from app.devices import crud as device_crud
from app.discovery.ping import check_device_status
from app.monitoring.model import MonitoringHistory
from database.database import SessionLocal

from .graph import TopologyGraphBuilder
from .schema import (
    SubnetInfo,
    TopologyGraphResponse,
    TopologySummary
)


def get_topology_graph(
    refresh_status: bool = False,
    include_wan: bool = True,
    connected_only: bool = True,
    source: str | None = None,
    grouping_network: str | None = None,
) -> TopologyGraphResponse:
    """
    Build and return the dynamic network topology graph.
    Combines registered devices, live/cached statuses, inferred links, and subnets.
    If connected_only is True, filters to only connect Online/discovered active devices.
    """
    db = SessionLocal()
    try:
        devices = device_crud.get_all_devices(source=source)

        statuses: dict[str, str] = {}
        latencies: dict[str, float | None] = {}

        if refresh_status and devices:
            # Concurrently check device statuses
            def _ping(dev):
                res = check_device_status(dev.ip)
                return dev.ip, res.get("status", "Offline")

            with ThreadPoolExecutor(max_workers=min(len(devices), 25)) as executor:
                results = list(executor.map(_ping, devices))
                for ip, st in results:
                    statuses[ip] = st
        else:
            try:
                recent_histories = (
                    db.query(MonitoringHistory)
                    .order_by(MonitoringHistory.checked_at.desc())
                    .limit(len(devices) * 3 if devices else 100)
                    .all()
                )
                for h in recent_histories:
                    if h.ip not in statuses:
                        statuses[h.ip] = h.status
            except Exception:
                recent_histories = []

            for d in devices:
                if d.ip not in statuses:
                    statuses[d.ip] = "Unknown"

        builder = TopologyGraphBuilder(
            devices=devices,
            statuses=statuses,
            latencies=latencies,
            include_wan=include_wan,
            connected_only=connected_only,
            grouping_network=grouping_network,
        )
        return builder.build()

    finally:
        db.close()


def get_topology_summary(connected_only: bool = True) -> TopologySummary:
    """Return high-level summary metrics of the network topology."""
    graph = get_topology_graph(refresh_status=False, include_wan=False, connected_only=connected_only)
    return graph.summary


def get_subnets(connected_only: bool = True) -> list[SubnetInfo]:
    """Return list of detected subnets and their host distribution."""
    graph = get_topology_graph(refresh_status=False, include_wan=False, connected_only=connected_only)
    return graph.subnets


def get_discovery_topology(
    network: str | None = None,
    auto_register: bool = False,
    include_wan: bool = True
) -> TopologyGraphResponse:
    """
    Discovers connected devices on the network and constructs a
    dynamic connected topology graph for discovered connected devices only.
    """
    from app.discovery.scanner import scan_network
    from app.devices.detector import detect_device_info

    target_network = network
    if not target_network:
        try:
            import socket
            import ipaddress
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
            target_network = str(ipaddress.ip_interface(f"{local_ip}/24").network)
        except Exception:
            target_network = "192.168.1.0/24"

    raw_devices = scan_network(target_network)
    online_ips = [d["ip"] for d in raw_devices if d.get("status") == "Online"]

    discovered = []
    max_workers = min(len(online_ips), 20) if online_ips else 1
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for info in executor.map(detect_device_info, online_ips):
            if info.get("status") == "Online":
                discovered.append({
                    "ip": info["ip"],
                    "name": info.get("hostname") or f"Device-{info['ip']}",
                    "device_type": info.get("device_type", "Unknown Device"),
                    "network_type": info.get("network_type", "Unknown"),
                    "source": "discovery",
                    "status": "Online",
                    "mac_address": info.get("mac_address"),
                    "open_ports": info.get("open_ports", []),
                    "is_gateway": info.get("is_gateway", False)
                })

    if auto_register:
        for dev_data in discovered:
            try:
                existing = device_crud.get_device_by_ip(dev_data["ip"])
                if not existing:
                    device_crud.create_device(
                        name=dev_data["name"],
                        ip=dev_data["ip"],
                        device_type=dev_data["device_type"],
                        network_type=dev_data["network_type"],
                        source="discovery",
                    )
            except Exception as e:
                print(f"Auto-register device error for {dev_data['ip']}: {type(e).__name__}: {e}")
                raise

    builder = TopologyGraphBuilder(
        devices=discovered,
        statuses={d["ip"]: "Online" for d in discovered},
        include_wan=include_wan,
        connected_only=True
    )
    return builder.build()
