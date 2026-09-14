@echo off
title STRICT SECURE FEDAVG (Real Training)
echo ====================================================
echo   STRICT Single-Key CKKS Simulation (Real Training)
echo   (Server NEVER decrypts)
echo ====================================================

set PYTHON_EXE="..\Complete Source Code\NewModel_active\demo_env\Scripts\python.exe"

echo [1/4] Generating Keys (Secret for Client, Public for Server)...
%PYTHON_EXE% setup.py

echo [2/4] Starting Server...
start "LG-IoV SERVER (STRICT)" cmd /k "%PYTHON_EXE% server.py"
timeout /t 3 /nobreak >nul

echo [3/4] Starting Client 1 (Training)...
start "LG-IoV CLIENT 1 (STRICT)" cmd /k "%PYTHON_EXE% client.py 1"

echo [4/4] Starting Client 2 (Training)...
start "LG-IoV CLIENT 2 (STRICT)" cmd /k "%PYTHON_EXE% client.py 2"

echo.
echo Real training demo running! Check the new windows.
pause
