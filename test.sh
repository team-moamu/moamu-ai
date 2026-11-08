#!/usr/bin/env bash
set -euo pipefail

if [[ $# -gt 3 ]]; then
  printf 'Usage: %s [image-key] [ai-task-id] [verification-id]\n' "$0" >&2
  exit 2
fi

IMAGE_KEY="${1:-artworks/girl_with_pearl_earring_studying.png}"
AI_TASK_ID="${2:-local-test-task-0587cc9c34284b029210fcf850169b7c}"
VERIFICATION_ID="${3:-local-test-verification-0587cc9c34284b029210fcf850169b7c}"
API_URL="${MOAMU_AI_URL:-http://127.0.0.1:8000/internal/photo-verifications}"

python3 - "$IMAGE_KEY" "$AI_TASK_ID" "$VERIFICATION_ID" <<'PY' | curl --request POST \
  --url "$API_URL" \
  --header 'Content-Type: application/json' \
  --silent \
  --show-error \
  --connect-timeout 5 \
  --max-time 60 \
  --fail-with-body \
  --data-binary @-
import json
import sys
from uuid import uuid4

image_key, ai_task_id, verification_id = sys.argv[1:]
request_id = uuid4().hex
payload = {
    "ai_task_id": ai_task_id or f"local-test-task-{request_id}",
    "verification_id": verification_id or f"local-test-verification-{request_id}",
    "image_key": image_key,
    "conditions": [
        {
            "code": "C1",
            "description": "책 또는 학습 노트가 사진에 보여야 한다",
        },
        {
            "code": "C2",
            "description": "직접 작성한 학습 메모가 사진에서 식별되어야 한다",
        },
        {
            "code": "C3",
            "description": "요약문 또는 문제 풀이 결과가 사진에 보여야 한다",
        },
    ],
}
json.dump(payload, sys.stdout, ensure_ascii=False)
PY
