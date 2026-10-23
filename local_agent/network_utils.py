
"""Shared network utilities for the NMVS Local Agent."""

import ipaddress
import platform
import re
import subprocess
from typing import Any


def ping(ip: str) -> dict[str, Any]:
    """Ping one IP address and return its status and latency."""

    address = str(ipaddress.ip_address(ip))

    if platform.system().lower() == "windows":
        command = ["ping", "-n", "1", "-w", "1000", address]
    else:
        command = ["ping", "-c", "1", "-W", "1", address]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=4,
            check=False,
            errors="replace",
        )
    except subprocess.TimeoutExpired:
        return {
            "ip": address,
            "status": "Offline",
            "latency_ms": None,
        }
    except OSError as exc:
        raise RuntimeError(f"Could not execute ping: {exc}") from exc

    output = f"{result.stdout}\n{result.stderr}"

    # Windows: time=2ms / time<1ms
    # Linux: time=2.34 ms
    match = re.search(
        r"time\s*[=<]\s*(\d+(?:\.\d+)?)\s*ms",
        output,
        re.IGNORECASE,
    )

    latency_ms = float(match.group(1)) if match else None

    return {
        "ip": address,
        "status": "Online" if result.returncode == 0 else "Offline",
        "latency_ms": latency_ms,
    }
