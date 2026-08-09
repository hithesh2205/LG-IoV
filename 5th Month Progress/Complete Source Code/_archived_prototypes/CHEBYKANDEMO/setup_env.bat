@echo off
REM ============================================================
REM  CHEBYKANDEMO — Virtual Environment Setup
REM  Creates a Python venv and installs all dependencies.
REM ============================================================

echo ============================================================
echo   ChebyKAN + CKKS FHE Demo — Environment Setup
echo ============================================================

REM Check Python is available
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python not found on PATH. Install Python 3.10+ first.
    pause
    exit /b 1
)

REM Create venv
if not exist "venv" (
    echo [1/3] Creating virtual environment...
    python -m venv venv
) else (
    echo [1/3] Virtual environment already exists, skipping creation.
)

REM Activate and install
echo [2/3] Activating venv and installing dependencies...
call venv\Scripts\activate.bat

python -m pip install --upgrade pip
pip install -r requirements.txt

echo.
echo [3/3] Verifying critical imports...
python -c "import torch; print(f'  torch {torch.__version__}')"
python -c "import tenseal; print(f'  tenseal {tenseal.__version__}')" 2>nul || (
    echo.
    echo [WARNING] TenSEAL failed to import.
    echo   On Windows, you may need:
    echo     pip install tenseal --no-build-isolation
    echo   Or install from a pre-built wheel:
    echo     pip install https://github.com/OpenMined/TenSEAL/releases/...
    echo   Requires Microsoft Visual C++ Build Tools.
)
python -c "import pandas; print(f'  pandas {pandas.__version__}')"
python -c "import numpy; print(f'  numpy {numpy.__version__}')"
python -c "import sklearn; print(f'  scikit-learn {sklearn.__version__}')"
python -c "import rich; print(f'  rich {rich.__version__}')"

echo.
echo ============================================================
echo   Setup complete! Activate with: venv\Scripts\activate
echo   Run smoke test:  python run_federated_fhe.py --dataset can_vtc --rounds 1 --smoke
echo ============================================================
pause
