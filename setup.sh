#!/usr/bin/env bash
set -e

echo "=============================================================================="
echo "                         LOCAL-CODER INSTALLATION SETUP"
echo "=============================================================================="

# Check Python 3
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 could not be found. Please install Python 3.10 or higher."
    exit 1
fi

echo "[INFO] Detected Python:"
python3 --version

# Create virtual environment if not present
if [ ! -d "venv" ]; then
    echo "[INFO] Creating virtual environment 'venv'..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip and install requirements
echo "[INFO] Upgrading pip..."
pip install --upgrade pip --quiet

echo "[INFO] Installing dependencies from requirements.txt..."
pip install -r requirements.txt

# Download / verify neural model weights
echo "[INFO] Verifying model weights..."
python3 scripts/download_model.py

echo ""
echo "=============================================================================="
echo "[SUCCESS] LOCAL-CODER setup complete and ready for use!"
echo ""
echo "1. Run full test suite:"
echo "    pytest tests -v"
echo ""
echo "2. Launch Developer Studio Web UI:"
echo "    python -m uvicorn local_coder.server.api_server:app --host 127.0.0.1 --port 8000"
echo ""
echo "3. Launch Interactive Terminal CLI:"
echo "    python -m local_coder.server.cli_app"
echo "=============================================================================="
