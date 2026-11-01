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

The provider sees the image plus each supplied condition ID and natural-language
description. It does not receive database codes, condition types, required flags,
or sort order. Prompt version `photo-verification-v2` asks the model to abstain
with `UNCERTAIN` where visual evidence is unclear. Gemini and Ollama use
constrained JSON output; the service validates provider output again before
returning it.

FastAPI request/response models follow the official [request body](https://fastapi.tiangolo.com/tutorial/body/)
pattern. Gemini uses the official [image input](https://ai.google.dev/gemini-api/docs/image-understanding)
and [structured output](https://ai.google.dev/gemini-api/docs/structured-output) interfaces.
Ollama uses its official [vision image input](https://docs.ollama.com/capabilities/vision),
[chat API](https://docs.ollama.com/api/chat), and [structured output](https://docs.ollama.com/capabilities/structured-outputs).
