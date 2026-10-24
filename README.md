# SignalStack

An incident-triage REST API and responsive dashboard built with **Python, FastAPI, SQLite, and JavaScript**. Built for a Unkey Compute demonstration.

## Features

- `POST /api/alerts` — ingest alerts, classify severity and group duplicates
- `GET /api/incidents` — retrieve the severity-prioritized incident queue
- `PATCH /api/incidents/{incident_id}` — update status to open, investigating or resolved
- `GET /api/stats` — totals for alerts, active incidents, grouped duplicates and critical issues
- `POST /api/demo` — add six sample alerts
- `GET /health` — health endpoint
- `/docs` — interactive API documentation
- `/` — responsive dashboard

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
