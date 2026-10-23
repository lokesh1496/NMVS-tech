"""NMVS Local Agent: ping registered devices from the Windows LAN and upload results."""
from __future__ import annotations
import ipaddress
import os
import platform
import re
import subprocess
import time
from typing import Any
from dotenv import load_dotenv
import requests

load_dotenv()
BACKEND_URL = os.getenv("NMVS_BACKEND_URL", "").strip().rstrip("/")
AGENT_TOKEN = os.getenv("NMVS_AGENT_TOKEN", "").strip()
INTERVAL_SECONDS = int(os.getenv("NMVS_AGENT_INTERVAL", "30"))
REQUEST_TIMEOUT_SECONDS = 20


def validate_config() -> None:
    if not BACKEND_URL:
        raise RuntimeError(
            "Set NMVS_BACKEND_URL in local_agent/.env"
        )

    if not BACKEND_URL.startswith(("http://", "https://")):
        raise RuntimeError(
            "NMVS_BACKEND_URL must start with http:// or https://"
        )

    # Allow HTTP only for local development.
    if BACKEND_URL.startswith("http://") and not any(
        host in BACKEND_URL
        for host in ("127.0.0.1", "localhost")
    ):
        raise RuntimeError(
            "HTTP is allowed only for localhost. Use HTTPS for deployed backends."
        )

    if len(AGENT_TOKEN) < 32:
        raise RuntimeError(
            "Set NMVS_AGENT_TOKEN to the same strong token configured on the backend."
        )

    if INTERVAL_SECONDS < 10:
        raise RuntimeError(
            "NMVS_AGENT_INTERVAL must be at least 10 seconds."
        )

def ping(ip: str) -> dict[str, Any]:
    """Ping one validated IPv4/IPv6 address and return status and parsed latency."""
    address = str(ipaddress.ip_address(ip))
    if platform.system().lower() == "windows":
        command = ["ping", "-n", "1", "-w", "1000", address]
    else:
        command = ["ping", "-c", "1", "-W", "1", address]

    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=4, check=False)
        output = f"{completed.stdout}\n{completed.stderr}"
        status = "Online" if completed.returncode == 0 else "Offline"
        latency_ms = None
        if status == "Online":
            match = re.search(r"(?:time|time<)\s*[=<]\s*([0-9]+(?:\.[0-9]+)?)\s*ms", output, re.I)
            if match:
                latency_ms = float(match.group(1))
            else:
                match = re.search(r"time\s*=\s*([0-9]+(?:\.[0-9]+)?)\s*ms", output, re.I)
                if match:
                    latency_ms = float(match.group(1))
        return {"ip": address, "status": status, "latency_ms": latency_ms}
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"Ping failed for {address}: {exc}")
        return {"ip": address, "status": "Offline", "latency_ms": None}


def api_headers() -> dict[str, str]:
    return {"X-Agent-Token": AGENT_TOKEN, "Accept": "application/json"}


def fetch_devices(session: requests.Session) -> list[dict[str, Any]]:
    response = session.get(
        f"{BACKEND_URL}/agent/devices",
        headers=api_headers(),
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    payload = response.json()
    devices = payload.get("devices", [])
    if not isinstance(devices, list):
        raise ValueError("Backend returned an invalid devices payload")
    return devices


def upload_results(session: requests.Session, results: list[dict[str, Any]]) -> None:
    if not results:
        return
    response = session.post(
        f"{BACKEND_URL}/agent/monitoring-results",
        headers=api_headers(),
        json={"results": results},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    print(f"Uploaded {len(results)} monitoring results: {response.status_code}")


def run_once(session: requests.Session) -> None:
    devices = fetch_devices(session)
    results: list[dict[str, Any]] = []
    for device in devices:
        ip = str(device.get("ip", "")).strip()
        try:
            results.append(ping(ip))
        except ValueError:
            print(f"Skipping invalid IP from backend: {ip!r}")
    if results:
        upload_results(session, results)
    else:
        print("No registered devices to monitor yet.")


def main() -> None:
    validate_config()
    print(f"NMVS Local Agent started. Backend: {BACKEND_URL}")
    print(f"Monitoring interval: {INTERVAL_SECONDS} seconds")
    with requests.Session() as session:
        while True:
            started = time.monotonic()
            try:
                run_once(session)
            except requests.RequestException as exc:
                print(f"Backend communication failed: {exc}")
            except Exception as exc:
                print(f"Agent cycle failed: {type(exc).__name__}: {exc}")
            elapsed = time.monotonic() - started
            time.sleep(max(1, INTERVAL_SECONDS - elapsed))


if __name__ == "__main__":

    main()
