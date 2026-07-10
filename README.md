# Investigator Agent — Person 3

The **Investigator** is the third stage of the automated job-failure diagnosis
pipeline. Triage hands it a failed job it couldn't resolve from rules; the
Investigator gathers evidence with tools and returns a structured **Diagnosis**.

```
Person 1        Person 2            >> Person 3 <<          Person 4
Ingestion  -->  Triage/Rules  -->   Investigator     -->   Explainer/Output
               (TriageObject)       (this package)         (Diagnosis)
```

**Acceptance criterion (met):** given a mocked triage object, the Investigator
calls at least two tools and returns a valid `Diagnosis`. It ships a
hardcoded/deterministic engine that runs *right now* with no network, and a
Claude tool-use engine that activates automatically when an API key is present.

## Quick start

```bash
# Runs offline out of the box (deterministic engine, no API key needed)
python run_investigator.py                # all three demo scenarios
python run_investigator.py dependency     # one scenario
python run_investigator.py code --json    # machine-readable Diagnosis

# Run the tests
python -m unittest discover -s tests -v   # (or: python -m pytest tests/)
```

To use the live Claude engine, install `anthropic` and set a key — the agent
auto-detects it:

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...       # PowerShell: $env:ANTHROPIC_API_KEY="..."
python run_investigator.py
```

If the LLM call fails for any reason, the agent falls back to the deterministic
engine rather than crashing.

## Public API (for Person 6 — integration)

```python
from investigator import investigate, Investigator, InvestigatorConfig
from investigator import TriageObject, Diagnosis, Category

# one-call:
diagnosis = investigate(triage_object)

# or configured:
agent = Investigator(InvestigatorConfig(use_llm=False, max_iterations=6))
diagnosis = agent.investigate(triage_object)
```

`investigate()` never raises — worst case it returns a low-confidence Diagnosis
with `needs_human=True`.

## The contracts (the seams)

Both objects have `to_dict()` / `from_dict()` so stages can hand off JSON across
processes/queues without importing this package. Full definitions in
`investigator/contracts.py`.

### Input — `TriageObject` (from Person 2)

| field | meaning |
|---|---|
| `incident_id` | unique id, echoed back on the Diagnosis |
| `job_id` | the failed job/service |
| `error_signature` | normalized error fingerprint (used to match memory) |
| `category` | triage's guess (`Category`, may be `unknown`) |
| `severity` | `low` / `medium` / `high` / `critical` |
| `error_excerpt` | the key error region (from Person 1) |
| `cleaned_log` | the ~100-line cleaned blob (from Person 1) |
| `escalated_reason` | why triage escalated instead of resolving |
| `metadata` | dict: `service`, `commit_sha`, `error_file`, `error_line`, `dependency`, ... |

### Output — `Diagnosis` (to Person 4)

| field | meaning |
|---|---|
| `incident_id` | matches the input |
| `root_cause` | the single most likely cause |
| `category` | resolved `Category` |
| `confidence` | `0.0`–`1.0`; `confidence_label` → `low`/`medium`/`high` |
| `recommended_fix` | concrete next step |
| `suggested_owner` | team to tag (nullable) |
| `evidence` | list of `Evidence(source, detail, snippet)` — traceable to the tool |
| `related_past_incidents` | ids of matched memory entries |
| `tools_used` | ordered list of tool calls |
| `reasoning_steps` | audit trail (incl. model thinking summaries) |
| `needs_human` | `True` when confidence is too low to act automatically |
| `model` | which engine produced it |

## How it works

Two engines behind one interface (`investigator/investigator.py`):

- **Deterministic engine** — calls the tools in a fixed, sensible order per
  category (always `query_past_incidents` + `search_logs` first, then
  category-specific corroboration), then synthesizes a Diagnosis from what came
  back. Offline, reproducible, ships first. This is the "hardcoded-tool version."
- **Claude engine** — a manual tool-use loop. The model calls investigation
  tools, reads results, and finally calls `submit_diagnosis` to stop. Uses
  `claude-opus-4-8` with adaptive thinking.

**Stop conditions** (Claude engine): the model calls `submit_diagnosis`; or the
loop hits `max_iterations` (then a Diagnosis is synthesized from evidence and
flagged); or the model ends its turn without a tool (nudged once toward a verdict).

**Confidence scoring** (`investigator/confidence.py`): an evidence-only heuristic
(more distinct tools, a matched past incident, a pinpointed code line/dead
dependency → higher) is blended with the model's self-reported confidence, so
thin-evidence over-confidence gets pulled down. The deterministic engine uses
the heuristic alone.

## Tools

Defined in `investigator/tools.py`, backed by offline fixtures in
`investigator/mock_data.py`:

| tool | purpose |
|---|---|
| `query_past_incidents` | search the memory store of past failures + fixes (Person 5's SQLite) |
| `search_logs` | grep the cleaned log |
| `read_code` | read source around a traceback `file:line` |
| `get_recent_deploys` | recent deploys/commits to catch regressions |
| `check_dependency_health` | status of a downstream dependency |
| `submit_diagnosis` | the stop tool the model calls to commit its verdict |

**Going live:** replace a tool's `run` implementation with one that hits the
real store, keeping the return shape. Nothing in the reasoning loop changes. In
particular, `query_past_incidents` should call Person 5's SQLite table.

## Layout

```
investigator/
  contracts.py     # TriageObject, Diagnosis, Evidence, Category (the seams)
  tools.py         # tool registry, JSON schemas, mock implementations
  investigator.py  # the two engines + confidence wiring + stop conditions
  confidence.py    # evidence heuristic + blend
  prompts.py       # system prompt + initial-message builder
  mock_data.py     # offline fixtures + 3 demo scenarios (one per category)
run_investigator.py  # demo CLI
tests/test_investigator.py
```
