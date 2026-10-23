
import threading
import requests

from network_utils import ping


def process_detection_job(session, backend_url, headers, job):
    job_id = job["job_id"]
    ip = job["ip"]

    result = ping(ip)

    response = session.post(
        f"{backend_url}/agent/detection-requests/{job_id}/result",
        headers=headers,
        json={
            "status": result["status"],
            "latency_ms": result.get("latency_ms"),
        },
        timeout=10,
    )
    response.raise_for_status()

    print(
        f"[Detection] Job {job_id}: {ip} -> "
        f"{result['status']} ({result.get('latency_ms')} ms)"
    )


def detection_worker(backend_url, headers, stop_event):
    with requests.Session() as session:
        while not stop_event.is_set():
            try:
                response = session.get(
                    f"{backend_url}/agent/detection-requests/next",
                    headers=headers,
                    timeout=10,
                )
                response.raise_for_status()

                job = response.json().get("job")

                if job:
                    try:
                        process_detection_job(
                            session, backend_url, headers, job
                        )
                    except Exception as exc:
                        print(
                            f"[Detection] Job {job.get('job_id')} "
                            f"failed: {exc}"
                        )
                else:
                    stop_event.wait(2)

            except requests.RequestException as exc:
                print(f"[Detection] Queue request failed: {exc}")
                stop_event.wait(3)
