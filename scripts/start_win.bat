@echo off
SETLOCAL

echo [GuanChao] Starting System in Dev Mode...
echo ------------------------------------------

:: 1. Start Backend in a new window
echo [1/2] Launching Backend...
start "GuanChao Backend" cmd /k "set PYTHONPATH=%~dp0..&& python -m backend.app.main"

:: 2. Start Frontend in a new window
echo [2/2] Launching Frontend...
cd %~dp0..\frontend
if not exist node_modules (
    echo Installing frontend dependencies...
    call npm install
)

start "GuanChao Frontend" cmd /k "npm run dev"

echo ------------------------------------------
echo System Started! 
echo Frontend: http://localhost:3000
echo Backend:  http://localhost:8000
echo (Close the new windows to stop servers)
pause
