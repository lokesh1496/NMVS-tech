# NMVS Frontend — Local Agent Detection

## What's changed
- Added API helpers for creating a LAN detection job and retrieving its status.
- Added a **LAN ping via Local Agent** panel to the Devices page.
- The panel creates a job using `POST /devices/detection-requests`, then checks `GET /devices/detection-requests/{job_id}` until the job completes or times out.
- Existing cloud-side device detection and inventory functionality are preserved.

## Requirements
- Backend must expose:
  - `POST /devices/detection-requests`
  - `GET /devices/detection-requests/{job_id}`
  - `GET /agent/detection-requests/next`
  - `POST /agent/detection-requests/{job_id}/result`
- User must be signed in.
- Local Agent must be running and configured with `NMVS_BACKEND_URL` pointing to the same backend used by the frontend.
- The backend database must contain the `detection_jobs` table.

## Configure API URL
Set `VITE_API_URL` in the frontend deployment environment to the backend base URL, e.g. `https://your-nmvs-backend.example` (no `/docs` or endpoint path). Do not put `NMVS_AGENT_TOKEN` in frontend environment variables.

## Build
```bash
npm install
npm run build
```

The uploaded `node_modules` folder is intentionally excluded from this source ZIP. Install dependencies on your machine/deployment environment before building.
