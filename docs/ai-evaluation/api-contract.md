# 내부 사진 판정 API

## 담당 범위

사진 업로드, MIME/파일 형식 및 용량 검사, 인증 시도 생성, 재시도·복구, 최종
`SUCCESS` / `FAILED` / `REVIEW_REQUIRED` 판정은 백엔드 담당이다. 이 서비스는
내부 테스트용 로컬/공유 볼륨 경로를 받아 확정된 인증 조건 스냅샷을 평가한다.
공유 볼륨은 아직 확정되지 않았으며 `AI_IMAGE_ROOT`가 서비스에서 읽을 수 있는
파일 범위를 제한한다.

기능 명세에는 각 상태와 함께 사유를 반환하라고 되어 있다. 이 대화에서 백엔드와
합의한 전달 형식은 상태만 반환하는 것이다. 따라서 현재 응답에는 조건 ID와 상태만
포함되며 모델 사유나 신뢰도 필드는 없다. 백엔드가 사용자 안내용 사유를 필요로 하면
계약을 다시 검토한다.

## `POST /internal/photo-verifications`

백엔드는 활성 도전의 인증 조건 스냅샷을 보낸다. AI 엔드포인트는 조건 유형을
추론하거나 조건 코드를 만들지 않는다. 전달받은 설명을 각각 판정하고 상태를
반환한다.

요청 본문:

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

위 예시는 공부 템플릿(`goal_template_id=3`)이다. 나머지 다섯 도전 템플릿도 같은
필드 구조를 사용하며 각 템플릿의 조건 행과 설명을 전달한다. 조건 스냅샷은 2~5개를
받고, 그중 필수 조건이 최소 2개여야 한다. `required`에는 백엔드의 `Y` / `N` 값을
사용한다(평가 매니페스트에서는 불리언을 사용할 수 있다). 백엔드 템플릿 시드에는
`goal_template_condition_id`가 있지만, 판정 요청에는 활성 도전 스냅샷의
`challenge_condition_id`를 사용해야 하며 이 값은 `verification_check`와 연결된다.
템플릿 ID, `goal_template_id`, 감사 시각은 AI 엔드포인트에 필요하지 않다.
지원하는 `condition_type` 값은 `OBJECT_PRESENT`, `ACTIVITY_IN_PROGRESS`,
`HANDWRITTEN_RECORD`, `SCREEN_RECORD`, `RESULT_OUTPUT`, `PLACE`, `DATE_VISIBLE`이며,
`DATE_VISIBLE`은 `required: "N"`으로 보내야 한다.

상태는 요청에 포함된 순서대로 반환한다. 서비스는 모델 응답에서 조건 ID가 누락되거나
추가되거나 중복되면 거부한다. 필수 조건 결과를 합쳐 최종 인증 상태를 계산하는 일은
백엔드 담당이다.

성공 응답:

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

오류 응답은 FastAPI의 `detail` 객체에 변하지 않는 `code`와 짧은 메시지를 담는다.

| HTTP | 코드 | 의미 |
|---:|---|---|
| 403 | `IMAGE_PATH_NOT_ALLOWED` | 확인된 파일이 `AI_IMAGE_ROOT` 바깥에 있음 |
| 404 | `IMAGE_NOT_FOUND` | 경로가 없거나 일반 파일이 아님 |
| 422 | `IMAGE_NOT_READABLE` | 파일을 읽을 수 없음 |
| 422 | 검증 오류 | 요청 또는 스키마가 올바르지 않음 |
| 502 | `INVALID_MODEL_OUTPUT` | 모델 응답이 조건 ID 또는 스키마와 일치하지 않음 |
| 503 | `IMAGE_ROOT_UNAVAILABLE` | 설정한 이미지 루트를 사용할 수 없음 |
| 503 | `AI_PROVIDER_NOT_CONFIGURED` | Gemini 키 또는 제공자 설정이 누락됨 |
| 503 | `AI_PROVIDER_ERROR` | 모델 요청이 실패했거나 시간 초과됨 |

이 엔드포인트는 로컬 경로의 존재 여부와 읽기 가능 여부만 확인한다. 이미지 MIME
유형이나 파일 용량은 검사하지 않는다. 로컬 개발에서는 `127.0.0.1`에 바인딩한다.
내부 서비스로 배포할 때는 외부에 노출하기 전에 네트워크를 격리하고 백엔드 서비스
인증을 추가해야 한다.

## 모델 입력·출력

모델에는 이미지와 각 조건의 ID·자연어 설명을 전달한다. v2 이후 버전은 DB 코드,
조건 유형, 필수 여부, 정렬 순서를 전달하지 않는다. 프롬프트 문구와 직렬화 방식은
`src/moamu_ai/prompts.py`에 버전별로 보존한다. `AI_PROMPT_VERSION`으로 서비스 버전을
선택하며 기본값은 `photo-verification-v4`다. 벤치마크 CLI는 `--prompt-version`으로
이를 덮어쓸 수 있다. v4는 조건에 명시된 대상·행동·형태의 시각적 증거를 요구하고,
이미지가 모호하거나 가려진 경우 `UNCERTAIN`을 반환한다. Gemini와 Ollama는 제한된
JSON 형식으로 응답하며, 서비스는 반환 전에 모델 응답을 다시 검증한다.

FastAPI 요청·응답 모델은 공식 [요청 본문 안내](https://fastapi.tiangolo.com/tutorial/body/)
방식을 따른다. Gemini는 공식 [이미지 입력](https://ai.google.dev/gemini-api/docs/image-understanding)과
[구조화된 출력](https://ai.google.dev/gemini-api/docs/structured-output) 인터페이스를 사용한다.
Ollama는 공식 [비전 이미지 입력](https://docs.ollama.com/capabilities/vision),
[채팅 API](https://docs.ollama.com/api/chat),
[구조화된 출력](https://docs.ollama.com/capabilities/structured-outputs)을 사용한다.
