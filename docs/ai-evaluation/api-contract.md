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

Request body:

```json
{
  "image_path": "attempts/123/proof.jpg",
  "conditions": [
    {
      "challenge_condition_id": 101,
      "code": "BOTTLE_VISIBLE",
      "condition_type": "OBJECT_VISIBLE",
      "description": "A water bottle is visible",
      "required": true,
      "sort_order": 1
    },
    {
      "challenge_condition_id": 102,
      "code": "DRINKING_VISIBLE",
      "condition_type": "ACTION_VISIBLE",
      "description": "A person is visibly drinking water",
      "required": true,
      "sort_order": 2
    }
  ]
}
```

Exactly two or three condition snapshots are accepted; at least two must be
required. `challenge_condition_id` maps directly to the ERD snapshot/result rows.
Statuses are returned in input order. The service rejects provider output with
missing, extra, or duplicate condition IDs.

Success response:

```json
{
  "results": [
    {"challenge_condition_id": 101, "status": "MET"},
    {"challenge_condition_id": 102, "status": "UNCERTAIN"}
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

The provider sees the image plus each supplied condition ID, code, type, and
description. Prompt version `photo-verification-v1` asks the model to abstain with
`UNCERTAIN` where visual evidence is unclear. Gemini and Ollama use constrained
JSON output; the service validates provider output again before returning it.

FastAPI request/response models follow the official [request body](https://fastapi.tiangolo.com/tutorial/body/)
pattern. Gemini uses the official [image input](https://ai.google.dev/gemini-api/docs/image-understanding)
and [structured output](https://ai.google.dev/gemini-api/docs/structured-output) interfaces.
Ollama uses its official [vision image input](https://docs.ollama.com/capabilities/vision),
[chat API](https://docs.ollama.com/api/chat), and [structured output](https://docs.ollama.com/capabilities/structured-outputs).
