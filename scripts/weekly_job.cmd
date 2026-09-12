@echo off
REM Phase 6 wrapper — Task Scheduler can point here.
cd /d "%~dp0\.."
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m src.agent.weekly_job --once --mode heuristic %*
) else (
  python -m src.agent.weekly_job --once --mode heuristic %*
)
exit /b %ERRORLEVEL%
