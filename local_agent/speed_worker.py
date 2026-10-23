"""Process queued Internet speed tests from the Local Agent computer."""

import threading

import requests

from speed_test import run_speed_test


def process_speed_test(session, backend_url, headers, job):
    job_id = job["job_id"]
    try:
        result = run_speed_test()
        payload = {"status": "completed", **result}
    except Exception as exc:
        payload = {
            "status": "failed",
            "error_message": f"{type(exc).__name__}: {exc}"[:1000],
        }

    response = session.post(
        f"{backend_url}/agent/speed-tests/{job_id}/result",
        headers=headers,
        json=payload,
        timeout=10,
    )
    response.raise_for_status()

    if payload["status"] == "completed":
        print(
            f"[Speed Test] Job {job_id}: "
            f"{payload['download_mbps']} Mbps down, "
            f"{payload['upload_mbps']} Mbps up, "
            f"{payload['ping_ms']} ms latency"
        )
    else:
        print(f"[Speed Test] Job {job_id} failed: {payload['error_message']}")


def speed_worker(backend_url, headers, stop_event: threading.Event):
    with requests.Session() as session:
        while not stop_event.is_set():
            try:
                response = session.get(
                    f"{backend_url}/agent/speed-tests/next",
                    headers=headers,
                    timeout=10,
                )
                response.raise_for_status()

                job = response.json().get("job")
                if job:
                    try:
                        process_speed_test(session, backend_url, headers, job)
                    except Exception as exc:
                        print(
                            f"[Speed Test] Job {job.get('job_id')} "
                            f"could not be reported: {exc}"
                        )
                else:
                    stop_event.wait(2)
            except requests.RequestException as exc:
                print(f"[Speed Test] Queue request failed: {exc}")
                stop_event.wait(3)
