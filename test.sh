#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  printf 'Usage: %s <image-path-relative-to-AI_IMAGE_ROOT>\n' "$0" >&2
  exit 2
fi

IMAGE_PATH="$1"
API_URL="${MOAMU_AI_URL:-http://127.0.0.1:8000/internal/photo-verifications}"

python3 - "$IMAGE_PATH" <<'PY' | curl --request POST \
  --url "$API_URL" \
  --header 'Content-Type: application/json' \
  --fail-with-body \
  --data-binary @-
import json
import sys

payload = {
    "image_path": sys.argv[1],
    "conditions": [
        {
            "challenge_condition_id": 301,
            "code": "C1",
            "condition_type": "OBJECT_PRESENT",
            "description": "책 또는 학습 노트가 사진에 보여야 한다",
            "required": "Y",
            "sort_order": 1,
        },
        {
            "challenge_condition_id": 302,
            "code": "C2",
            "condition_type": "HANDWRITTEN_RECORD",
            "description": "직접 작성한 학습 메모가 사진에서 식별되어야 한다",
            "required": "Y",
            "sort_order": 2,
        },
        {
            "challenge_condition_id": 303,
            "code": "C3",
            "condition_type": "RESULT_OUTPUT",
            "description": "학습한 내용을 정리한 요약문 또는 문제 풀이 결과가 사진에 보여야 한다",
            "required": "Y",
            "sort_order": 3,
        },
        {
            "challenge_condition_id": 304,
            "code": "C4",
            "condition_type": "PLACE",
            "description": "학습 자료를 놓은 책상이나 학습 공간이 사진에서 확인되어야 한다",
            "required": "Y",
            "sort_order": 4,
        },
        {
            "challenge_condition_id": 305,
            "code": "C5",
            "condition_type": "DATE_VISIBLE",
            "description": "학습 기록에 적힌 날짜가 사진에서 식별되어야 한다",
            "required": "N",
            "sort_order": 5,
        },
    ],
}
json.dump(payload, sys.stdout, ensure_ascii=False)
PY
