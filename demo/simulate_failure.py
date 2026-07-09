"""
Fire a simulated pipeline failure at the orchestrator and print the result.

Usage:
    python demo/simulate_failure.py           # defaults to dbt
    python demo/simulate_failure.py airflow
    python demo/simulate_failure.py dbt
    python demo/simulate_failure.py fivetran
"""
import sys
import json
import argparse
from pathlib import Path
import httpx

ORCHESTRATOR = "http://localhost:8000"
SAMPLES = Path(__file__).parent / "sample_logs"

TOOLS = {
    "airflow":  ("airflow",  SAMPLES / "airflow_failure.json"),
    "dbt":      ("dbt",      SAMPLES / "dbt_failure.json"),
    "fivetran": ("fivetran", SAMPLES / "fivetran_failure.json"),
}

parser = argparse.ArgumentParser()
parser.add_argument("tool", nargs="?", default="dbt", choices=list(TOOLS))
parser.add_argument("--channel", default="#data-alerts")
args = parser.parse_args()

tool, sample_file = TOOLS[args.tool]
raw_payload = json.loads(sample_file.read_text())

print(f"\n Firing {tool.upper()} failure → orchestrator...")

try:
    resp = httpx.post(
        f"{ORCHESTRATOR}/failure",
        json={"tool": tool, "raw_payload": raw_payload, "slack_channel": args.channel},
        timeout=90,
    )
    resp.raise_for_status()
except httpx.ConnectError:
    print("Cannot reach orchestrator at localhost:8000. Run start_all.bat first.")
    sys.exit(1)
except httpx.HTTPStatusError as e:
    print(f"Error {e.response.status_code}: {e.response.text}")
    sys.exit(1)

result = resp.json()
d = result["diagnosis"]
o = result["owner"]

print("=" * 60)
print(f"  JOB:       {d['job_name']}")
print(f"  SEVERITY:  {d['severity'].upper()}  |  CONFIDENCE: {d['confidence'].upper()}")
print(f"  OWNER:     {o['name']} ({o['slack_handle']})")
print("=" * 60)
print(f"\nROOT CAUSE\n{d['root_cause']}")
print(f"\nSUGGESTED FIX\n{d['suggested_fix']}")
print("\n Slack notification sent!")
print("=" * 60)
