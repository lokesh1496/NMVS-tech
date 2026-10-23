from . import crud
from .speed_test import run_speed_test


def run_live_test(ip: str = "internet") -> dict:
    """
    Run a live speed test without saving it to the database.
    """
    return run_speed_test(ip)


def run_and_save(ip: str = "internet") -> dict:
    """
    Run a live speed test and save the results into the database history.
    """
    result = run_speed_test(ip)

    if result.get("error"):
        raise RuntimeError(result["error"])

    record = crud.save_result(
        ip=result["ip"],
        download_mbps=result["download_mbps"],
        upload_mbps=result["upload_mbps"],
        ping_ms=result.get("ping_ms")
    )
    return record.to_dict()


def get_history(limit: int = 20, ip: str = None) -> list:
    """
    Retrieve past speed test records from the database.
    """
    records = crud.get_history(limit=limit, ip=ip)
    return [r.to_dict() for r in records]


def get_history_by_id(history_id: int) -> dict | None:
    """
    Retrieve a specific speed test record by ID from the database.
    """
    record = crud.get_history_by_id(history_id)
    return record.to_dict() if record else None


def delete_history(history_id: int) -> bool:
    """
    Delete a specific speed test record from the database.
    """
    return crud.delete_history_item(history_id)
