#!/usr/bin/env bash
# Build the single-file desktop executable for the host platform (macOS / Linux).
# Produces dist/ftf-local. On Windows, run the equivalent in CI (windows-latest).
set -euo pipefail
cd "$(dirname "$0")/.."

python -m pip install -q --upgrade pyinstaller
DATA_SEP=":"; [[ "${OS:-}" == "Windows_NT" ]] && DATA_SEP=";"

python -m PyInstaller \
  --noconfirm --clean --onefile \
  --name ftf-local \
  --add-data "app/static${DATA_SEP}app/static" \
  --add-data "stub${DATA_SEP}stub" \
  --collect-submodules uvicorn \
  --collect-submodules fastapi \
  --hidden-import app.worker \
  --hidden-import stub.compute \
  --exclude-module celery \
  --exclude-module kombu \
  --exclude-module boto3 \
  --exclude-module botocore \
  desktop.py

echo "built: dist/ftf-local"
