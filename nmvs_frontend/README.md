# NMVS Frontend

Standalone React + Vite application for the existing FastAPI NMVS backend. It lives in `nmvs_frontend` and does not modify backend source or routes.

## Requirements

- Node.js 20 or newer
- The NMVS FastAPI backend running at `http://127.0.0.1:8000` (or a configured API URL)

## Run locally

From this folder:

```powershell
npm install
Copy-Item .env.example .env
npm run dev
```

Open the Vite URL printed in the terminal (normally `http://localhost:5173`). Set `VITE_API_URL` in `.env` if the backend is hosted elsewhere. Restart Vite after changing environment variables.

## Backend integration

The API modules in `src/api` follow routes, methods, authorization requirements, and schemas defined in the neighboring `backend/app` source:

- Authentication: login, register, forgot password, verify reset OTP, reset password, current user, and authenticated password change.
- Dashboard: `/dashboard/overview`.
- Devices: list, create, read, update, delete, detect, and re-detect.
- Discovery: backend-side CIDR scan and single-IP ping through the connected Local Agent.
- Monitoring: recent history, per-IP history, and live check.
- Topology: server-supplied graph and live refresh.
- Speed monitoring: on-demand Internet speed test from the connected Local Agent, saved history, and history deletion. The entered IP/name is a history label; throughput is measured to Cloudflare, not to that device.
- Alerts: list/summary, acknowledge, resolve, and delete.
- Reports: device CSV and executive PDF downloads.
- Metrics: network summary and uptime for a selected window.
- Settings: account profile, supported preferences, and password change.

The Local Agent must be running and connected to the same backend for single-IP discovery pings and speed tests. CIDR scans still run from the backend host; a cloud backend cannot scan a private LAN that it cannot access. Error, loading, and empty states are shown instead of sample records.

The scan endpoint currently returns only IP and status for reachable devices; the UI does not fabricate hostnames or types. Monitoring history currently contains status and check time but no latency. Topology visualizes only nodes and edges returned by the backend. The `backend/app/logs` source folder is not registered as a router in `backend/main.py`, so there is no logs API to integrate and no logs page is presented.

## Single-web-service Render deployment

The repository-root `Dockerfile` builds the frontend and backend into one Render web service. Create a Docker-based web service from the repository root (do not set a root directory), add a Render PostgreSQL database, and set these variables on the web service:

- `DATABASE_URL`: the PostgreSQL database's internal connection URL.
- `NMVS_ENVIRONMENT`: `production`.
- `NMVS_SECRET_KEY`: a private random value of at least 32 characters.

Generate the frontend build without `VITE_API_URL` so the deployed UI calls the API on the same origin. Set the health check path to `/health`. The web service serves the frontend at `/` and keeps the API available at paths such as `/docs` and `/health`. Run the Local Agent on a computer that can reach the LAN for single-IP pings and speed tests. CIDR scans run from the backend host and require that host to have access to the scanned network.

## Build

```sh
npm run build
```
