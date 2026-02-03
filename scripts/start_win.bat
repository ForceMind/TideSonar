@echo off
SETLOCAL

echo [GuanChao] Starting System in Dev Mode...
echo ------------------------------------------

:: Ask for License securely (Current Session Only)
echo.
set /p USER_LICENSE="Enter Biying License (Leave empty for Mock Mode): "

if "%USER_LICENSE%"=="" (
    echo [Config] No license provided. System will run in MOCK MODE.
    set "BIYING_LICENSE="
) else (
    echo [Config] License received. System will run in REAL MODE.
    set "BIYING_LICENSE=%USER_LICENSE%"
)
echo.

:: 1. Start Backend in a new window
echo [1/2] Launching Backend...
:: Resolve Project Root (Parent of scripts folder)
pushd %~dp0..
set "PROJECT_ROOT=%CD%"
popd

:: Launch in new window, setting workdir to Project Root
start "GuanChao Backend" /D "%PROJECT_ROOT%" cmd /k "set PYTHONPATH=%PROJECT_ROOT%&& set BIYING_LICENSE=%BIYING_LICENSE%&& python backend\app\main.py"

:: 2. Start Frontend in a new window (Frontend doesn't need the key, backend handles data)
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
