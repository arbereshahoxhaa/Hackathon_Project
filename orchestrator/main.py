import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="PipelineDoc Orchestrator")

LOG_COLLECTOR  = os.getenv("LOG_COLLECTOR_URL",  "http://localhost:8001")
DIAGNOSIS      = os.getenv("DIAGNOSIS_URL",       "http://localhost:8002")
OWNERSHIP      = os.getenv("OWNERSHIP_URL",       "http://localhost:8003")
NOTIFICATION   = os.getenv("NOTIFICATION_URL",    "http://localhost:8004")

TIMEOUT = httpx.Timeout(120.0)   # two Claude calls in the pipeline (Agent 1 + Agent 2)


class FailureRequest(BaseModel):
    tool: str
    raw_payload: dict
    slack_channel: str = "#data-alerts"


@app.get("/health")
def health():
    return {"status": "ok", "service": "orchestrator", "port": 8000}


@app.post("/failure")
def handle_failure(request: FailureRequest):
    with httpx.Client(timeout=TIMEOUT) as client:

        # Step 1 — Parse, normalise, and enrich logs (Agent 1)
        r = client.post(f"{LOG_COLLECTOR}/collect",
                        json={"tool": request.tool, "raw_payload": request.raw_payload})
        _check(r, "log-collector")
        normalized = r.json()

        # Step 2 — Root cause analysis (Agent 2) — receives enriched CollectedFailure
        r = client.post(f"{DIAGNOSIS}/diagnose", json=normalized)
        _check(r, "diagnosis")
        diagnosis = r.json()

        # Step 3 — Resolve owner
        r = client.post(f"{OWNERSHIP}/route", json={"job_name": normalized["job_name"]})
        _check(r, "ownership-router")
        owner = r.json()

        # Step 4 — Notify Slack
        r = client.post(f"{NOTIFICATION}/notify",
                        json={"diagnosis": diagnosis, "owner": owner,
                              "slack_channel": request.slack_channel})
        _check(r, "notification")
        notification = r.json()

    return {"normalized": normalized, "diagnosis": diagnosis, "owner": owner, "notification": notification}


def _check(response: httpx.Response, service: str):
    if response.status_code >= 400:
        raise HTTPException(status_code=502,
                            detail=f"{service} error {response.status_code}: {response.text}")
