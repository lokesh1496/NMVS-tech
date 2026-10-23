# NMVS Backend (reviewed build)

## Included corrections

- Removed the real `.env` file from the deliverable; configure your own local `.env` from `.env.example`.
- Removed wildcard CORS origins and the permissive origin regex. Set explicit frontend origins with `CORS_ALLOWED_ORIGINS`.
- Required authentication for `GET /auth/users`.
- Prevented password-reset OTPs from being written to logs or returned after SMTP delivery fails; failed delivery invalidates the stored OTP.
- Avoided returning raw database exception details to API clients.
- Removed hard-coded database and SMTP credential fallbacks; PostgreSQL now fails fast if required connection variables are missing.
- Removed the static development JWT secret fallback; development uses an ephemeral key when none is configured, and production requires a strong explicit key.
- Sanitized database diagnostics so passwords and raw exception details are not returned.
- Initialized database tables in the service tests so the suite runs consistently from a clean checkout.

## Setup

1. Install Python 3.11+ (Python 3.12 is a good default) and PostgreSQL only if you intend to use it.
2. Create an environment: `python -m venv .venv`
3. Activate it, then install dependencies: `pip install -r requirements.txt`
4. Copy `.env.example` to `.env`. For local development, leave `DATABASE_URL` blank to use SQLite. For PostgreSQL, set `DATABASE_URL` to a SQLAlchemy URL such as `postgresql+psycopg2://user:password@localhost:5432/nmvs` and URL-encode reserved characters in credentials. The legacy `DB_TYPE=postgres` and `POSTGRES_*` settings remain supported.
5. Generate a JWT secret with `python -c "import secrets; print(secrets.token_urlsafe(48))"` and set `NMVS_SECRET_KEY` in `.env`. In production, set `NMVS_ENVIRONMENT=production` and use a unique random secret of at least 32 characters. The development fallback is ephemeral and invalidates tokens after restart.
6. Configure `SMTP_USERNAME`, `SMTP_PASSWORD`, and optionally `SMTP_FROM_EMAIL` if password-reset emails are needed. For Gmail, use `smtp.gmail.com`, port `587`, the full Gmail address as `SMTP_USERNAME`, and a Google app password (not your normal account password) as `SMTP_PASSWORD`. If `SMTP_FROM_EMAIL` is unset, the authenticated username is used. If the API cannot deliver the email, `/auth/forgot-password` returns `503` instead of claiming it was sent; check the backend log for the SMTP failure, and check Spam/Junk in the recipient mailbox.
7. The frontend queues speed tests for the Local Agent, which measures its computer's Internet connection using Cloudflare's HTTPS test service. The agent computer needs outbound HTTPS access to `speed.cloudflare.com`. The existing direct backend speed-test API remains available separately.
8. Start the API from this directory: `uvicorn main:app --reload`
9. Open `/docs` for the API documentation.

## Verification

- Syntax check: `python -m compileall -q app database main.py tests`
- Tests: `python -m unittest discover -s tests -v`

The reviewed build passed all 21 bundled unit tests in the supplied environment. That is not a substitute for an integration test against your actual frontend, SMTP account, and target database.

## Security before deployment

**The original uploaded ZIP contained real SMTP and database credentials. Rotate those credentials immediately**, especially the SMTP app password, and do not reuse the old values. Keep `.env` out of source control and shared ZIPs. Replace the development JWT secret with a long, random, unique value before deployment.
