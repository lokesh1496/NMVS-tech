# NMVS Backend — Detection Queue Update

This package contains the backend source from the uploaded project, including the local-agent detection queue routes.

## Important files
- `main.py` registers `agent_router` and `detection_requests_router`.
- `app/agent/detection_model.py` defines the `detection_jobs` table.
- `app/agent/detection_routes.py` exposes authenticated user endpoints:
  - `POST /devices/detection-requests`
  - `GET /devices/detection-requests/{job_id}`
- `app/agent/router.py` exposes agent-token endpoints:
  - `GET /agent/detection-requests/next`
  - `POST /agent/detection-requests/{job_id}/result`

## Local setup
1. Back up your existing `backend` folder before replacing files.
2. Do **not** overwrite or share your real `.env`. This archive deliberately excludes `.env`, local database files, and Python cache files.
3. In the backend folder, create/retain your `.env` with the correct local values. See `.env.example` for variable names.
4. Activate your virtual environment and install dependencies if needed:
   `pip install -r requirements.txt`
5. Start the API from this folder:
   `uvicorn main:app --reload`
6. Open `http://127.0.0.1:8000/openapi.json` and search for `/devices/detection-requests`.
7. Open `http://127.0.0.1:8000/docs`. The endpoints are grouped under the separate **Device Detection** tag, not under **Devices**.

## Database note
The `DetectionJob` model is imported in `main.py` before `init_db()` runs, so `Base.metadata.create_all()` can create the table for a local SQLite database during application startup. If you run the one-line `create_all` check manually, it creates only the table if missing:
`python -c "from sqlalchemy import inspect; from database.database import Base, engine; from app.agent.detection_model import DetectionJob; Base.metadata.create_all(bind=engine, tables=[DetectionJob.__table__]); print(inspect(engine).has_table('detection_jobs'))"`

The local SQLite database is separate from the production Neon PostgreSQL database. Production needs its own schema/table setup and the code deployed to the backend host.

## Authentication
`POST /devices/detection-requests` and `GET /devices/detection-requests/{job_id}` require the app's normal user authentication. Agent endpoints require `X-Agent-Token`, which must match `NMVS_AGENT_TOKEN` on the backend and Local Agent. Use a fresh, high-entropy token; do not share it in screenshots or chat.
