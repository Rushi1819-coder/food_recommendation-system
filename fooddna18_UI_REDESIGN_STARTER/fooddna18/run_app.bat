@echo off
title Food DNA - Launcher
echo ========================================================
echo               FOOD DNA APPLICATION LAUNCHER             
echo ========================================================
echo.

cd /d "%~dp0"
if exist "fooddna18" (
    cd fooddna18
)

echo [1/3] Starting Backend API Server (Port 5000)...
start "Food DNA - Backend API (Port 5000)" cmd /k "call .\venv\Scripts\activate.bat && python run.py"

echo [2/3] Starting Frontend Server (Port 5500)...
start "Food DNA - Frontend (Port 5500)" cmd /k "cd frontend && python -m http.server 5500"

echo [3/3] Opening Food DNA in your default browser...
timeout /t 2 /nobreak >nul
start http://127.0.0.1:5500

echo.
echo ========================================================
echo Application is now running!
echo - Frontend URL: http://127.0.0.1:5500
echo - Backend API:  http://127.0.0.1:5000
echo.
echo Demo Accounts:
echo - Customer:         customer@gmail.com   (Password: Password123!)
echo - Restaurant Admin: restaurant@gmail.com (Password: Password123!)
echo - Kitchen Staff:    staff@gmail.com      (Password: Password123!)
echo - Delivery Partner: delivery@gmail.com   (Password: Password123!)
echo - Super Admin:      admin@gmail.com      (Password: Password123!)
echo ========================================================
echo Keep this window open or close it when done.
pause
