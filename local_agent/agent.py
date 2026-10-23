
"""NMVS Local Agent: monitor registered devices and process detection jobs."""

from __future__ import annotations

import os
import time
import threading
from typing import Any

import requests
from dotenv import load_dotenv

from network_utils import ping
from detection_worker import detection_worker


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
            "HTTP is allowed only for localhost. "
            "Use HTTPS for deployed backends."
        )

    if len(AGENT_TOKEN) < 32:
        raise RuntimeError(
            "Set NMVS_AGENT_TOKEN to the same strong token "
            "configured on the backend."
        )

    if INTERVAL_SECONDS < 10:
        raise RuntimeError(
            "NMVS_AGENT_INTERVAL must be at least 10 seconds."
        )


def api_headers() -> dict[str, str]:
    return {
        "X-Agent-Token": AGENT_TOKEN,
        "Accept": "application/json",
    }


def fetch_devices(
    session: requests.Session,
) -> list[dict[str, Any]]:
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


def upload_results(
    session: requests.Session,
    results: list[dict[str, Any]],
) -> None:
    if not results:
        return

    response = session.post(
        f"{BACKEND_URL}/agent/monitoring-results",
        headers=api_headers(),
        json={"results": results},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()

    print(
        f"Uploaded {len(results)} monitoring results: "
        f"{response.status_code}"
    )


def run_once(session: requests.Session) -> None:
    """Monitor registered devices; preserve the existing workflow."""
    devices = fetch_devices(session)
    results = []

    for device in devices:
        ip = device.get("ip")

        if not ip:
            continue

        try:
            result = ping(ip)
            results.append(result)

            print(
                f"Device: {result['ip']} | "
                f"Status: {result['status']} | "
                f"Latency: {result.get('latency_ms')} ms"
            )

        except Exception as exc:
            print(f"Device: {ip} | Error: {exc}")

    if results:
        upload_results(session, results)
    else:
        print("No valid registered devices to monitor.")


def main() -> None:
    validate_config()

    print(f"NMVS Local Agent started. Backend: {BACKEND_URL}")
    print(f"Monitoring interval: {INTERVAL_SECONDS} seconds")

    stop_event = threading.Event()

    # Separate thread for on-demand IP detection.
    detection_thread = threading.Thread(
        target=detection_worker,
        args=(BACKEND_URL, api_headers(), stop_event),
        name="nmvs-detection-worker",
        daemon=True,
    )
    detection_thread.start()

    try:
        # Existing registered-device monitoring loop.
        with requests.Session() as session:
            while True:
                started = time.monotonic()

                try:
                    run_once(session)

                except requests.RequestException as exc:
                    print(f"Backend communication failed: {exc}")

                except Exception as exc:
                    print(
                        f"Agent cycle failed: "
                        f"{type(exc).__name__}: {exc}"
                    )

                elapsed = time.monotonic() - started
                time.sleep(max(1, INTERVAL_SECONDS - elapsed))

    except KeyboardInterrupt:
        print("\nStopping NMVS Local Agent...")

    finally:
        stop_event.set()
        detection_thread.join(timeout=3)
        print("NMVS Local Agent stopped.")


if __name__ == "__main__":
    main()
