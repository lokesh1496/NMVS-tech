import platform
import subprocess
import ipaddress


def check_device_status(ip: str) -> dict:
    """
    Check whether a device is reachable via ping.
    Returns {"ip": ip, "status": "Online" | "Offline"}
    """
    ip_str = str(ip)

    try:
        ipaddress.ip_address(ip_str)
    except ValueError:
        return {"ip": ip_str, "status": "Offline"}

    if platform.system().lower() == "windows":
        command = ["ping", "-n", "1", "-w", "1000", ip_str]
    else:
        command = ["ping", "-c", "1", "-W", "1", ip_str]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True
        )
        status = "Online" if result.returncode == 0 else "Offline"
    except Exception:
        status = "Offline"

    return {
        "ip": ip_str,
        "status": status
    }


def ping_device(ip: str) -> dict:
    return check_device_status(ip)