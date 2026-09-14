@echo off
title LG-IoV Federated Learning CLI Simulation (CKKS)
echo ====================================================
echo   LG-IoV Federated Learning CLI Simulation (CKKS)
echo ====================================================
echo.
echo Starting the Server (RSU) ...
start "LG-IoV SERVER" cmd /k "demo_env\Scripts\python.exe demo_server.py"

echo Waiting 5 seconds for Server to initialize CKKS Context ...
timeout /t 5 /nobreak >nul

echo Starting Vehicle Client 1 ...
start "LG-IoV CLIENT 1" cmd /k "demo_env\Scripts\python.exe demo_client.py --id 1"

echo Starting Vehicle Client 2 ...
start "LG-IoV CLIENT 2" cmd /k "demo_env\Scripts\python.exe demo_client.py --id 2"

echo.
echo Demo is running! Check the 3 new command prompt windows.
pause
