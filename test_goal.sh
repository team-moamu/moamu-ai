#!/usr/bin/env bash
# 실행 중인 로컬 API에 자유목표 사진 인증 가능 여부를 요청한다.
set -euo pipefail

if [[ $# -gt 2 ]]; then
  printf 'Usage: %s [goal] [category-path-json|null]\n' "$0" >&2
  printf 'Example: %s "매일 영어 표현 적기" '\''{"major":"학습","middle":"외국어","minor":"작문"}'\''\n' "$0" >&2
  exit 2
fi

GOAL="${1:-매일 영어 뉴스 10분 듣고 새로 들은 표현 적기}"
CATEGORY_PATH_JSON="${2:-null}"
API_URL="${MOAMU_AI_URL:-http://127.0.0.1:8000/internal/goals/evaluate-verifiability}"

python3 - "$GOAL" "$CATEGORY_PATH_JSON" <<'PY' | curl --request POST \
  --url "$API_URL" \
  --header 'Content-Type: application/json' \
  --silent \
  --show-error \
  --connect-timeout 5 \
  --max-time 90 \
  --fail-with-body \
  --data-binary @-
import json
import sys

goal, category_path_json = sys.argv[1:]
try:
    category_path = json.loads(category_path_json)
except json.JSONDecodeError as exc:
    raise SystemExit(f"category-path-json must be valid JSON: {exc}") from exc

payload = {"goal": goal, "categoryPath": category_path}
json.dump(payload, sys.stdout, ensure_ascii=False)
PY
