import os
import statistics
import time
from concurrent.futures import ThreadPoolExecutor

import requests


_BASE_URL = "https://speed.cloudflare.com"
_DOWNLOAD_SIZE = 5_000_000
_UPLOAD_SIZE = 1_000_000
_PARALLEL_REQUESTS = 4
_TIMEOUT = (10, 60)


def _get_ping_ms() -> float:
    samples = []
    for index in range(5):
        started = time.perf_counter()
        response = requests.get(
            f"{_BASE_URL}/__down",
            params={"bytes": 1, "nonce": f"{time.time_ns()}-{index}"},
            timeout=_TIMEOUT,
        )
        response.raise_for_status()
        if not response.content:
            raise RuntimeError("Speed-test server returned an empty ping response")
        samples.append((time.perf_counter() - started) * 1000)
    return round(statistics.median(samples), 2)


def _download_bytes(index: int) -> int:
    response = requests.get(
        f"{_BASE_URL}/__down",
        params={"bytes": _DOWNLOAD_SIZE, "nonce": f"{time.time_ns()}-{index}"},
        headers={"Cache-Control": "no-cache"},
        timeout=_TIMEOUT,
    )
    response.raise_for_status()
    if not response.content:
        raise RuntimeError("Speed-test server returned an empty download")
    return len(response.content)


def _upload_bytes(index: int) -> int:
    payload = os.urandom(_UPLOAD_SIZE)
    response = requests.post(
        f"{_BASE_URL}/__up",
        data=payload,
        headers={
            "Cache-Control": "no-cache",
            "Content-Type": "application/octet-stream",
        },
        timeout=_TIMEOUT,
    )
    response.raise_for_status()
    return len(payload)


def _measure_transfer(
    transfer,
    request_count: int = _PARALLEL_REQUESTS,
) -> float:
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=request_count) as executor:
        byte_counts = list(executor.map(transfer, range(request_count)))
    elapsed = time.perf_counter() - started
    total_bytes = sum(byte_counts)
    if total_bytes <= 0 or elapsed <= 0:
        raise RuntimeError("Speed test transferred no data")
    return round((total_bytes * 8) / elapsed / 1_000_000, 2)


def run_speed_test(ip: str = "internet") -> dict:
    """Measure this machine's internet download, upload, and HTTP latency."""
    ip_str = str(ip).strip() if ip else "internet"
    try:
        ping_ms = _get_ping_ms()
        download_mbps = _measure_transfer(_download_bytes)
        upload_mbps = _measure_transfer(_upload_bytes, request_count=1)
        return {
            "ip": ip_str,
            "download_mbps": download_mbps,
            "upload_mbps": upload_mbps,
            "ping_ms": ping_ms,
            "server": "Cloudflare",
            "isp": None,
            "client_ip": None,
            "error": None,
        }
    except requests.RequestException as exc:
        raise RuntimeError(
            f"Speed test could not reach its HTTPS test service ({type(exc).__name__})"
        ) from exc
