# NMVS Local Agent (initial monitoring foundation)

This agent runs on a Windows laptop that can reach the monitored LAN. It polls the deployed backend for registered device IPs, pings them locally, and uploads status/latency results over HTTPS.

## 1. Configure backend

Set `NMVS_AGENT_TOKEN` in the backend host environment to a unique random secret of at least 32 characters. Never commit the real token to source control. Redeploy the backend after adding the variable.

## 2. Run locally on Windows

Open PowerShell in this folder:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

Set `NMVS_BACKEND_URL` to the deployed backend HTTPS URL and `NMVS_AGENT_TOKEN` to the same secret configured on the backend. Then load the variables into the current PowerShell session (PowerShell does not automatically load `.env`):

```powershell
$env:NMVS_BACKEND_URL="https://YOUR-BACKEND-DOMAIN"
$env:NMVS_AGENT_TOKEN="YOUR_SAME_RANDOM_SECRET"
$env:NMVS_AGENT_INTERVAL="30"
python .\agent.py
```

The agent only monitors IPs already registered in the NMVS device inventory. Add a reachable test device in the existing website first. This first phase does not yet move interactive CIDR discovery or detailed hostname/MAC/port detection into the agent; those are later integration steps.

## Security notes

- Use HTTPS only.
- Keep the token out of Git, frontend variables, logs, and screenshots.
- This initial version uses a shared agent token; rotate it if exposed.
- The agent should run only on a network you own or are authorized to monitor.
