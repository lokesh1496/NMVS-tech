# NMVS Local Agent

This agent runs on a Windows computer that can reach the monitored LAN. It polls the NMVS backend for registered devices, pings them locally, uploads status/latency results, processes single-IP ping requests, and runs on-demand Internet speed tests from this computer.

## Run the complete project locally

1. Start the backend on `http://127.0.0.1:8000` by following [the backend setup guide](../backend/README_BACKEND.md).
2. Start the frontend on `http://localhost:5173` by following [the frontend setup guide](../nmvs_frontend/README.md). Its `.env.example` already points `VITE_API_URL` to the local backend.
3. From this folder, install and configure the Local Agent:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   Copy-Item .env.example .env
   notepad .env
   ```

Set `NMVS_BACKEND_URL` to `http://127.0.0.1:8000`. Generate a random token with `python -c "import secrets; print(secrets.token_urlsafe(32))"` and put the exact same value in `NMVS_AGENT_TOKEN` in both `backend/.env` and `local_agent/.env`. Do not use the example placeholder as a production token. The agent loads its `.env` automatically when started from this folder:

   ```powershell
   python .\agent.py
   ```

The backend and agent must run on the same computer for the localhost URL above. If the agent runs on a different computer, use the backend computer's reachable LAN address instead of `127.0.0.1` and configure the backend to allow that frontend origin.

## Environment and security

- Keep real `.env` files out of Git. Only `.env.example` templates belong in the repository.
- Use the same strong `NMVS_AGENT_TOKEN` in the backend and agent.
- Use HTTPS for a deployed backend; HTTP is allowed only for localhost.
- - The agent can monitor registered device IPs, ping one explicitly entered address, and measure this computer's Internet connection using Cloudflare's speed-test service.
- CIDR network discovery still runs from the backend host; the Local Agent does not perform network-range scans.
- Rebuild the Local Agent executable after updating its Python source so the executable includes the speed-test worker.
