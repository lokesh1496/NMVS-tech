import platform
import subprocess


def check_device_status(ip: str) -> dict:
    """
    Check whether a device is reachable.

    Returns:
        {
            "ip": "...",
            "status": "Online" or "Offline"
        }
    """

    if platform.system().lower() == "windows":
        command = ["ping", "-n", "1", "-w", "1000", ip]
    else:
        command = ["ping", "-c", "1", "-W", "1", ip]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            status = "Online"
        else:
            status = "Offline"

    except Exception:
        status = "Offline"

    return {
        "ip": ip,
        "status": status
    }