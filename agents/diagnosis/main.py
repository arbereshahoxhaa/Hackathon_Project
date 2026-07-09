import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import os
import json
import anthropic
from fastapi import FastAPI, HTTPException
from models import NormalizedFailure, DiagnosisResult
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Diagnosis Agent")
_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

_SYSTEM = """You are a senior data engineer and on-call expert.
Diagnose the pipeline failure and respond with ONLY valid JSON — no markdown, no extra text.

Schema:
{
  "root_cause": "plain-English explanation of what went wrong and why",
  "suggested_fix": "concrete action the engineer should take right now",
  "severity": "low | medium | high",
  "confidence": "low | medium | high"
}"""


@app.get("/health")
def health():
    return {"status": "ok", "service": "diagnosis", "port": 8002}


@app.post("/diagnose", response_model=DiagnosisResult)
def diagnose(failure: NormalizedFailure):
    prompt = f"""Pipeline failure — please diagnose.

Tool: {failure.tool}
Job: {failure.job_name}
Environment: {failure.environment}
Error: {failure.error_message}

Log excerpt:
{failure.log_excerpt}"""

    try:
        response = _client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Claude API error: {exc}")

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    data = json.loads(raw)
    return DiagnosisResult(
        **failure.model_dump(),
        root_cause=data["root_cause"],
        suggested_fix=data["suggested_fix"],
        severity=data.get("severity", "medium"),
        confidence=data.get("confidence", "medium"),
    )
