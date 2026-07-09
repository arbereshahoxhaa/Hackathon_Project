import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from models import DiagnosisResult, OwnerInfo
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Notification Agent")
_slack = WebClient(token=os.environ.get("SLACK_BOT_TOKEN", ""))
_EMOJI = {"high": ":red_circle:", "medium": ":large_yellow_circle:", "low": ":large_green_circle:"}


class NotifyRequest(BaseModel):
    diagnosis: DiagnosisResult
    owner: OwnerInfo
    slack_channel: str = "#data-alerts"


@app.get("/health")
def health():
    return {"status": "ok", "service": "notification", "port": 8004}


@app.post("/notify")
def notify(request: NotifyRequest):
    d = request.diagnosis
    channel = os.environ.get("SLACK_CHANNEL", request.slack_channel)
    emoji = _EMOJI.get(d.severity, ":white_circle:")

    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": f"{emoji}  Pipeline Failure — {d.job_name}"}},
        {"type": "divider"},
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Tool:*\n{d.tool.upper()}"},
                {"type": "mrkdwn", "text": f"*Environment:*\n{d.environment}"},
                {"type": "mrkdwn", "text": f"*Severity:*\n{d.severity.capitalize()}"},
                {"type": "mrkdwn", "text": f"*Owner:*\n{request.owner.slack_handle}"},
            ],
        },
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*:mag: Root Cause*\n{d.root_cause}"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*:wrench: Suggested Fix*\n{d.suggested_fix}"}},
    ]

    fallback = f"[{d.severity.upper()}] {d.tool.upper()} failure in {d.job_name}: {d.root_cause[:200]}"

    try:
        resp = _slack.chat_postMessage(channel=channel, text=fallback, blocks=blocks)
        return {"ok": True, "ts": resp["ts"], "channel": resp["channel"]}
    except SlackApiError as exc:
        raise HTTPException(status_code=502, detail=f"Slack error: {exc.response['error']}")
