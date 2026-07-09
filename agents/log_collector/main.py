import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from models import NormalizedFailure

app = FastAPI(title="Log Collector Agent")


class RawEvent(BaseModel):
    tool: str
    raw_payload: dict


@app.get("/health")
def health():
    return {"status": "ok", "service": "log-collector", "port": 8001}


@app.post("/collect", response_model=NormalizedFailure)
def collect(event: RawEvent):
    parsers = {"airflow": _airflow, "dbt": _dbt, "fivetran": _fivetran}
    parser = parsers.get(event.tool)
    if not parser:
        raise HTTPException(status_code=400, detail=f"Unsupported tool: {event.tool}")
    fields = parser(event.raw_payload)
    return NormalizedFailure(tool=event.tool, **fields)


def _airflow(p: dict) -> dict:
    log = p.get("log", "")
    log_excerpt = "\n".join(log[-30:]) if isinstance(log, list) else str(log)[-2000:]
    return {
        "job_name": f"{p.get('dag_id', 'unknown')}.{p.get('task_id', 'unknown')}",
        "error_message": p.get("exception", "No exception provided"),
        "log_excerpt": log_excerpt,
        "timestamp": p.get("execution_date", datetime.utcnow().isoformat()),
        "run_id": p.get("run_id"),
        "environment": p.get("environment", "production"),
    }


def _dbt(p: dict) -> dict:
    steps = p.get("runSteps", [])
    failed = next((s for s in steps if s.get("status") == "error"), {})
    logs = failed.get("logs", p.get("logs", "No log output"))
    log_excerpt = "\n".join(logs[-30:]) if isinstance(logs, list) else str(logs)[-2000:]
    return {
        "job_name": p.get("jobName", "unknown_job"),
        "error_message": failed.get("statusMessage", p.get("statusMessage", "dbt run failed")),
        "log_excerpt": log_excerpt,
        "timestamp": p.get("runStartedAt", datetime.utcnow().isoformat()),
        "run_id": str(p.get("runId", "")),
        "environment": p.get("environmentName", "production"),
    }


def _fivetran(p: dict) -> dict:
    data = p.get("data", {})
    connector = p.get("connector_name", p.get("connector_id", "unknown"))
    schema = p.get("schema_name", "")
    return {
        "job_name": f"{connector}/{schema}" if schema else connector,
        "error_message": data.get("failure_message") or data.get("reason", "Fivetran sync failed"),
        "log_excerpt": str(data.get("message", ""))[-2000:],
        "timestamp": p.get("created", datetime.utcnow().isoformat()),
        "run_id": data.get("task_id"),
        "environment": p.get("environment", "production"),
    }
