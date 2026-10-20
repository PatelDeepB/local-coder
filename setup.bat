@echo off
setlocal enabledelayedexpansion

echo ==============================================================================
echo                         LOCAL-CODER INSTALLATION SETUP
echo ==============================================================================

:: Check Python installation
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not installed or not in PATH. Please install Python 3.10 or higher.
    exit /b 1
)

:: Display Python version
echo [INFO] Detected Python:
python --version

:: Create virtual environment if not already present
if not exist "venv" (
    echo [INFO] Creating virtual environment 'venv'...
    python -m venv venv
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        exit /b 1
    )
)

:: Activate virtual environment
call venv\Scripts\activate.bat

:: Upgrade pip
echo [INFO] Upgrading pip...
python -m pip install --upgrade pip --quiet

:: Install dependencies
echo [INFO] Installing required dependencies from requirements.txt...
pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to install dependencies.
    exit /b 1
)

:: Download / verify neural model weights
echo [INFO] Verifying model weights...
python scripts\download_model.py
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to download model weights.
    exit /b 1
)

echo.
echo ==============================================================================
echo [SUCCESS] LOCAL-CODER setup complete and ready for use!
echo.
echo 1. Run full test suite:
echo     pytest tests -v
echo.
echo 2. Launch Developer Studio Web UI:
echo     python -m uvicorn local_coder.server.api_server:app --host 127.0.0.1 --port 8000
echo.
echo 3. Launch Interactive Terminal CLI:
echo     python -m local_coder.server.cli_app
echo ==============================================================================
