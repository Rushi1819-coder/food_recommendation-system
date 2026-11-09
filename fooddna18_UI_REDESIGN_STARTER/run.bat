@echo off
setlocal
cd /d "%~dp0"

if exist "fooddna18" (
    cd fooddna18
)
if exist "fooddna18_UI_REDESIGN_STARTER\fooddna18" (
    cd fooddna18_UI_REDESIGN_STARTER\fooddna18
)

if exist ".\venv\Scripts\python.exe" (
    set "PY_EXE=.\venv\Scripts\python.exe"
) else (
    set "PY_EXE=python"
)

"%PY_EXE%" run.py %*
