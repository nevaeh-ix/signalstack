import os
import tempfile
os.environ["DATABASE_PATH"] = tempfile.mktemp(prefix="signalstack-", suffix=".db")
from fastapi.testclient import TestClient
from main import app

def test_incident_deduplication():
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        a = client.post("/api/alerts", json={"service":"checkout","message":"Database timeout after 3000ms"})
        b = client.post("/api/alerts", json={"service":"checkout","message":"Database timeout after 4000ms"})
        assert a.status_code == b.status_code == 201
        assert b.json()["deduplicated"] is True
        assert b.json()["incident"]["occurrences"] == 2
        assert client.get("/api/stats").json()["duplicates_suppressed"] == 1
