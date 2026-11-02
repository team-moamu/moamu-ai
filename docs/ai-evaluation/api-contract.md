# Internal photo-verification API

## Ownership

The backend owns photo upload, MIME/type and size checks, attempt creation,
durable retry/recovery, and the overall `SUCCESS` / `FAILED` /
`REVIEW_REQUIRED` decision. This service receives a local/shared-volume path for
internal testing and evaluates the frozen condition snapshot. The shared volume is
not finalized; `AI_IMAGE_ROOT` bounds the files the service can read.

The feature specification asks for a reason alongside each status. The backend
handoff agreed in this session asks this endpoint to return statuses only. The
current response therefore contains condition ID and status; it has no model
reason or confidence field. Revisit this contract if the backend requires a reason
for user-facing explanations.

## `POST /internal/photo-verifications`

The backend sends the active challenge's condition snapshots. The AI endpoint
does not infer condition types or create condition codes; it judges each supplied
description and returns its status.

Request body:

```json
{
  "image_path": "attempts/123/proof.jpg",
  "conditions": [
    {
      "challenge_condition_id": 301,
      "code": "C1",
      "condition_type": "OBJECT_PRESENT",
      "description": "책 또는 학습 노트가 사진에 보여야 한다",
      "required": "Y",
      "sort_order": 1
    },
    {
      "challenge_condition_id": 302,
      "code": "C2",
      "condition_type": "HANDWRITTEN_RECORD",
      "description": "직접 작성한 학습 메모가 사진에서 식별되어야 한다",
      "required": "Y",
      "sort_order": 2
    },
    {
      "challenge_condition_id": 303,
      "code": "C3",
      "condition_type": "RESULT_OUTPUT",
      "description": "학습한 내용을 정리한 요약문 또는 문제 풀이 결과가 사진에 보여야 한다",
      "required": "Y",
      "sort_order": 3
    },
    {
      "challenge_condition_id": 304,
      "code": "C4",
      "condition_type": "PLACE",
      "description": "학습 자료를 놓은 책상이나 학습 공간이 사진에서 확인되어야 한다",
      "required": "Y",
      "sort_order": 4
    },
    {
      "challenge_condition_id": 305,
      "code": "C5",
      "condition_type": "DATE_VISIBLE",
      "description": "학습 기록에 적힌 날짜가 사진에서 식별되어야 한다",
      "required": "N",
      "sort_order": 5
    }
  ]
}
```

The sample above is the study template (`goal_template_id=3`). The same field
shape can be used for all six challenge templates, while each template supplies
its own condition rows and descriptions. Two to five condition snapshots are
accepted; at least two must be required.
`required` accepts the backend's `Y` / `N` values (evaluation manifests may use
booleans). The backend's template seed uses `goal_template_condition_id`, but a
verification request must use the active challenge snapshot's
`challenge_condition_id`, which maps to `verification_check`. The template ID,
`goal_template_id`, and audit timestamp are not needed by the AI endpoint.
The supported `condition_type` values are `OBJECT_PRESENT`,
`ACTIVITY_IN_PROGRESS`, `HANDWRITTEN_RECORD`, `SCREEN_RECORD`, `RESULT_OUTPUT`,
`PLACE`, and `DATE_VISIBLE`; `DATE_VISIBLE` should be sent with `required: "N"`.

Statuses are returned in input order. The service rejects provider output with
missing, extra, or duplicate condition IDs. The backend remains responsible for
combining required-condition results into the overall verification state.

Success response:

```json
{
  "results": [
    {"challenge_condition_id": 301, "status": "MET"},
    {"challenge_condition_id": 302, "status": "MET"},
    {"challenge_condition_id": 303, "status": "UNCERTAIN"},
    {"challenge_condition_id": 304, "status": "MET"},
    {"challenge_condition_id": 305, "status": "NOT_MET"}
  ]
}
```

Error responses use FastAPI's `detail` object with a stable `code` and a short
message:

| HTTP | Code | Meaning |
|---:|---|---|
| 403 | `IMAGE_PATH_NOT_ALLOWED` | Resolved file is outside `AI_IMAGE_ROOT` |
| 404 | `IMAGE_NOT_FOUND` | Path is missing or not a regular file |
| 422 | `IMAGE_NOT_READABLE` | File cannot be read |
| 422 | validation error | Invalid request/schema |
| 502 | `INVALID_MODEL_OUTPUT` | Provider output did not match the condition IDs/schema |
| 503 | `IMAGE_ROOT_UNAVAILABLE` | Configured image root is unavailable |
| 503 | `AI_PROVIDER_NOT_CONFIGURED` | Gemini key/provider configuration is missing |
| 503 | `AI_PROVIDER_ERROR` | Provider request failed or timed out |

This endpoint checks local path existence/readability only. It does not validate
image MIME type or file size. It binds to `127.0.0.1` for local development; a
deployed internal service needs network isolation and backend service
authentication before exposure.

## Model input/output

모델에는 이미지와 각 조건의 ID·자연어 설명을 전달한다. v2 이후 버전은 DB 코드,
조건 유형, 필수 여부, 정렬 순서를 전달하지 않는다. 프롬프트 문구와 직렬화 방식은
`src/moamu_ai/prompts.py`에 버전별로 보존한다. `AI_PROMPT_VERSION`으로 서비스 버전을
선택하며 기본값은 `photo-verification-v4`다. 벤치마크 CLI는 `--prompt-version`으로
이를 덮어쓸 수 있다. v4는 조건에 명시된 대상·행동·형태의 시각적 증거를 요구하고,
이미지가 모호하거나 가려진 경우 `UNCERTAIN`을 반환한다. Gemini와 Ollama는 제한된
JSON 형식으로 응답하며, 서비스는 반환 전에 모델 응답을 다시 검증한다.

FastAPI request/response models follow the official [request body](https://fastapi.tiangolo.com/tutorial/body/)
pattern. Gemini uses the official [image input](https://ai.google.dev/gemini-api/docs/image-understanding)
and [structured output](https://ai.google.dev/gemini-api/docs/structured-output) interfaces.
Ollama uses its official [vision image input](https://docs.ollama.com/capabilities/vision),
[chat API](https://docs.ollama.com/api/chat), and [structured output](https://docs.ollama.com/capabilities/structured-outputs).
