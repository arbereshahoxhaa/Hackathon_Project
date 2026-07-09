@echo off
cd /d "%~dp0"
echo Starting all PipelineDoc services...

start "log-collector"    cmd /k "uvicorn agents.log_collector.main:app --port 8001 --reload"
start "diagnosis"        cmd /k "uvicorn agents.diagnosis.main:app --port 8002 --reload"
start "ownership-router" cmd /k "uvicorn agents.ownership_router.main:app --port 8003 --reload"
start "notification"     cmd /k "uvicorn agents.notification.main:app --port 8004 --reload"
start "orchestrator"     cmd /k "uvicorn orchestrator.main:app --port 8000 --reload"

echo.
echo All services started:
echo   Orchestrator   http://localhost:8000
echo   Log Collector  http://localhost:8001
echo   Diagnosis      http://localhost:8002
echo   Ownership      http://localhost:8003
echo   Notification   http://localhost:8004
echo.
echo Run demo: python demo\simulate_failure.py dbt
