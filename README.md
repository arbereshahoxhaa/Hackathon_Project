# PipelineDoc

AI-powered pipeline failure diagnosis. When a scheduled job fails, PipelineDoc reads the logs, identifies the root cause, and posts a plain-English summary to Slack — tagging the right owner.

## How it works

```
Raw logs → Log Collector → Diagnosis (Claude) → Owner Lookup → Slack Notification
```

Four agents run in sequence (steps 2 and 3 run in parallel):

| Agent | Port | Role |
|---|---|---|
| Log Collector | 8001 | Parses Airflow / dbt / Fivetran logs, extracts key fields |
| Diagnosis | 8002 | Claude performs root cause analysis |
| Ownership Router | 8003 | Looks up the on-call owner from `pipeline_owners.yaml` |
| Notification | 8004 | Posts a formatted alert to Slack |
| Orchestrator | 8000 | Chains all four agents |
| Frontend | 8501 | Streamlit UI |

---

## Prerequisites

- Python 3.12
- An Anthropic API key
- (Optional) A Slack bot token for real Slack posting — without one the alert prints to the console

---

## Setup

**1. Clone and enter the project**
```bash
git clone <repo-url>
cd Hackathon_Project
```

**2. Create and activate a virtual environment**
```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Mac / Linux
source .venv/bin/activate
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Configure environment variables**
```bash
copy .env.example .env   # Windows
cp .env.example .env     # Mac / Linux
```

Edit `.env` and fill in:
```
ANTHROPIC_API_KEY=sk-ant-...
SLACK_BOT_TOKEN=xoxb-...      # optional — leave blank to use console fallback
SLACK_CHANNEL=#data-alerts
```

**5. (Optional) Edit pipeline owners**

Open `pipeline_owners.yaml` and map your job name patterns to team members.

---

## Run

**Activate your venv first**, then launch everything with one command:

```bash
# Windows
.venv\Scripts\activate
start_all.bat
```

This opens six terminal windows (five backend services + the Streamlit UI).

**Open the UI:** http://localhost:8501

---

## Demo a failure

### Option A — Browser UI (recommended for demos)

1. Open http://localhost:8501
2. Select a tool (dbt / Airflow / Fivetran) in the sidebar
3. Click **Diagnose Failure**

### Option B — CLI

```bash
python demo/simulate_failure.py dbt
python demo/simulate_failure.py airflow
python demo/simulate_failure.py fivetran
```

### Option C — Direct API call

```bash
curl -X POST http://localhost:8000/failure \
  -H "Content-Type: application/json" \
  -d '{"tool": "dbt", "raw_payload": {...}, "slack_channel": "#data-alerts"}'
```

---

## Health check

```bash
curl http://localhost:8000/health
```

Returns the status of all downstream services.

---

## Project structure

```
Hackathon_Project/
├── orchestrator/main.py          # Chains all agents, parallel execution
├── agents/
│   ├── log_collector/main.py     # Agent 1: parse + enrich logs (Claude)
│   ├── diagnosis/main.py         # Agent 2: root cause analysis (Claude)
│   ├── ownership_router/main.py  # Agent 3: YAML owner lookup
│   └── notification/main.py      # Agent 4: Slack post
├── frontend/app.py               # Streamlit UI
├── models.py                     # Shared Pydantic models
├── pipeline_owners.yaml          # Job → owner mapping
├── demo/
│   ├── simulate_failure.py       # CLI demo script
│   └── sample_logs/              # Sample Airflow / dbt / Fivetran payloads
├── start_all.bat                 # One-command launch (Windows)
├── requirements.txt
└── .env.example
```
