# SignalStack

An incident-triage dashboard with a key-free browser demo and an optional **Python, FastAPI, and SQLite** backend.

## Website

[Open SignalStack](https://nevaeh-ix.github.io/signalstack/)

The GitHub Pages dashboard processes alerts, groups duplicates, prioritizes incidents and saves status changes in your browser. No API key, paid hosting or server setup is needed. Click **Load demo data** to try it.

Both `index.html` and `static/index.html` run the same browser dashboard. Data stays on the browser and device you use. If browser storage is unavailable, the dashboard still works for the current tab and shows a notice. Classification uses keyword rules.

Run the dashboard checks with `node tests/test_dashboard.cjs`.

## Optional backend API

- `POST /api/alerts` — ingest alerts, classify severity and group duplicates
- `GET /api/incidents` — retrieve the severity-prioritized incident queue
- `PATCH /api/incidents/{incident_id}` — update status to open, investigating or resolved
- `GET /api/stats` — totals for alerts, active incidents, grouped duplicates and critical issues
- `POST /api/demo` — add six sample alerts
- `GET /health` — health endpoint
- `/docs` — interactive API documentation
- `/` — browser dashboard (stores incidents locally; API records are separate)

## Local setup

```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8080
```

Visit http://localhost:8080. API docs: http://localhost:8080/docs.

## API example

```bash
curl -X POST http://localhost:8080/api/alerts \
  -H 'Content-Type: application/json' \
  -d '{"service":"checkout-api","message":"Database timeout after 3000ms"}'
```

Send another alert with a different timeout number. SignalStack normalizes numbers and groups these alerts as one incident, incrementing the occurrence count.

## Unkey Compute

1. Connect this GitHub repository to a new Compute app in [Unkey](https://app.unkey.com/).
2. Select the main branch and deploy. The included Dockerfile serves FastAPI at `0.0.0.0` with the configured `PORT`.
3. Open the deployment URL, try the dashboard and verify `/health` and `/docs`.

**Demo limitations:** Incidents are stored in local SQLite under `/tmp/signalstack.db` by default. Container filesystem state may reset or diverge between instances. Production usage needs persistent storage, authentication, and rate limiting. Severity classification is rules-based, not an ML model.

## Stack

Python · FastAPI · Pydantic · SQLite · JavaScript · Docker · OpenAPI

