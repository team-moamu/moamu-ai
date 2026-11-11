#!/usr/bin/env bash
# 로컬 가상환경을 활성화하고 개발용 FastAPI 서버를 실행한다.
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

if [[ ! -f .venv/bin/activate ]]; then
  printf 'Virtual environment not found. Create it with: python3 -m venv .venv\n' >&2
  exit 1
fi

source .venv/bin/activate
exec uvicorn moamu_ai.app:app --reload --host 127.0.0.1 --port 8000
