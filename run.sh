#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

source .venv/bin/activate
exec uvicorn moamu_ai.app:app --reload --host 127.0.0.1 --port 8000
