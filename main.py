import hashlib
import os
import re
import sqlite3
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

ROOT = Path(__file__).parent
DB_PATH = os.getenv("DATABASE_PATH", "/tmp/signalstack.db")
LOCK = threading.RLock()

def db():
    connection = sqlite3.connect(DB_PATH, timeout=15)
    connection.row_factory = sqlite3.Row
    return connection

def init():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with db() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fingerprint TEXT NOT NULL UNIQUE,
            service TEXT NOT NULL,
            message TEXT NOT NULL,
            severity TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            occurrences INTEGER NOT NULL DEFAULT 1,
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            recommendation TEXT NOT NULL
        )""")

@asynccontextmanager
async def lifespan(app):
    init()
    yield

app = FastAPI(title="SignalStack API", version="1.0.0", lifespan=lifespan)

class Alert(BaseModel):
    service: str = Field(min_length=2, max_length=80)
    message: str = Field(min_length=4, max_length=500)
    severity: Literal["auto","low","medium","high","critical"] = "auto"

class Status(BaseModel):
    status: Literal["open","investigating","resolved"]

def classify(message):
    m = message.lower()
    rules = [
        (("outage","service down","data breach","unauthorized"),"critical","Escalate to on-call and check the blast radius."),
        (("timeout","database","unavailable","connection refused","latency","500 error"),"high","Check dependencies, latency, logs and recent deploys."),
        (("429","rate limit","retry","queue backlog"),"medium","Inspect traffic and queue metrics."),
        (("warning","deprecated","cache miss"),"low","Monitor trends and schedule a fix.")
    ]
    for terms, severity, recommendation in rules:
        if any(term in m for term in terms):
            return severity, recommendation
    return "medium", "Review logs and traces to identify the cause."

def fingerprint(service, message):
    normalized = re.sub(r"\d+", "<num>", re.sub(r"\s+", " ", message.lower().strip()))
    return hashlib.sha256((service + ":" + normalized).encode()).hexdigest()[:20]

@app.get("/", include_in_schema=False)
def home():
    return FileResponse(ROOT / "static" / "index.html")

@app.get("/health")
def health():
    return {"status":"ok","service":"signalstack"}

@app.post("/api/alerts", status_code=201)
def ingest(alert: Alert):
    service, message = alert.service.strip().lower(), alert.message.strip()
    if len(service) < 2 or len(message) < 4:
        raise HTTPException(422, "Service or message too short")
    key = fingerprint(service, message)
    inferred, recommendation = classify(message)
    severity = inferred if alert.severity == "auto" else alert.severity
    now = datetime.now(timezone.utc).isoformat()
    with LOCK:
        with db() as c:
            old = c.execute("SELECT * FROM incidents WHERE fingerprint=?", (key,)).fetchone()
            if old:
                ranks = {"low":0,"medium":1,"high":2,"critical":3}
                severity = max((old["severity"], severity), key=lambda s: ranks[s])
                c.execute("UPDATE incidents SET occurrences=occurrences+1, last_seen=?, status='open', severity=? WHERE id=?", (now, severity, old["id"]))
                row = c.execute("SELECT * FROM incidents WHERE id=?", (old["id"],)).fetchone()
            else:
                c.execute("INSERT INTO incidents (fingerprint,service,message,severity,first_seen,last_seen,recommendation) VALUES (?,?,?,?,?,?,?)", (key,service,message,severity,now,now,recommendation))
                row = c.execute("SELECT * FROM incidents WHERE fingerprint=?", (key,)).fetchone()
            return {"deduplicated":old is not None, "incident":dict(row)}

@app.get("/api/incidents")
def incidents(status: Literal["all","open","investigating","resolved"]="all", limit: int=Query(50,ge=1,le=200)):
    where = "" if status=="all" else " WHERE status=?"
    params = [] if status=="all" else [status]
    sql = "SELECT * FROM incidents" + where + " ORDER BY CASE severity WHEN 'critical' THEN 4 WHEN 'high' THEN 3 WHEN 'medium' THEN 2 ELSE 1 END DESC, last_seen DESC LIMIT ?"
    with db() as c:
        return {"incidents":[dict(x) for x in c.execute(sql, params+[limit])]}

@app.patch("/api/incidents/{incident_id}")
def set_status(incident_id: int, update: Status):
    with LOCK:
        with db() as c:
            result = c.execute("UPDATE incidents SET status=? WHERE id=?", (update.status,incident_id))
            if not result.rowcount:
                raise HTTPException(404,"Incident not found")
            return {"incident":dict(c.execute("SELECT * FROM incidents WHERE id=?", (incident_id,)).fetchone())}

@app.get("/api/stats")
def stats():
    with db() as c:
        n = c.execute("SELECT COUNT(*) AS incidents, COALESCE(SUM(occurrences),0) AS events FROM incidents").fetchone()
        active = c.execute("SELECT COUNT(*) FROM incidents WHERE status!='resolved'").fetchone()[0]
        critical = c.execute("SELECT COUNT(*) FROM incidents WHERE severity='critical' AND status!='resolved'").fetchone()[0]
        return {"total_alerts":n["events"],"total_incidents":n["incidents"],"active_incidents":active,"duplicates_suppressed":n["events"]-n["incidents"],"active_critical":critical}

@app.post("/api/demo")
def demo():
    samples = [
        ("checkout-api","Database timeout after 3000ms"),
        ("checkout-api","Database timeout after 4500ms"),
        ("auth-service","Unauthorized access detected"),
        ("worker","Queue backlog of 500 jobs"),
        ("gateway","Rate limit 429 exceeded"),
        ("catalog","Cache miss warning")
    ]
    return {"results":[ingest(Alert(service=s,message=m)) for s,m in samples]}
