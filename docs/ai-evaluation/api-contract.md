# 내부 AI 사진 판정 API 계약

## 담당 범위

백엔드는 인증 사진 업로드, 이미지 형식·용량 검사, `verification` 및 `ai_task`
생성, 재시도와 작업 복구, 최종 인증 상태 결정을 담당한다. AI 서버는 저장된
사진을 읽고 요청에 포함된 모든 인증 조건을 각각 판정한다. 전체 인증 결과는
AI 서버가 합산하지 않는다.

## 백엔드 DB 기준

이 계약은 백엔드 저장소의 Flyway 마이그레이션 파일 V1~V6을 기준으로 한다. V3~V5에서
조건 테이블의 `condition_type`, `required`, `sort_order`가 제거됐고 V6은 `users.login_id`만
변경하므로 사진 판정 요청에는 영향을 주지 않는다. 백엔드는 현재 조건의 `code`,
`description`과 사진의 S3 `image_key`를 AI 서버에 전달한다.

평가 데이터의 `ConditionSnapshot`에 남아 있는 `condition_type`, `required`, `sort_order`는
실험 데이터용 메타데이터다. 최신 백엔드 DB 컬럼이나 AI HTTP 요청 필드가 아니다. 실제
적용 버전은 환경의 Flyway 이력으로 확인해야 한다.

## `POST /internal/photo-verifications`

백엔드 서버에서만 호출하는 내부 API다. JSON 요청의 조건에는 백엔드 DB의 내부
ID, 조건 유형, 필수 여부, 정렬 순서를 포함하지 않는다. AI 서버는 요청된 각
조건을 판정하고 같은 조건 `code`를 사용해 결과를 돌려준다.

이 프로토타입은 요청 헤더 기반 서비스 인증을 정의하지 않는다. 배포 시에는 AI
서버를 내부 네트워크에만 노출하고 백엔드 서버만 접근하도록 네트워크 정책을
설정해야 한다.

### 요청

```json
{
  "ai_task_id": "1",
  "verification_id": "1",
  "image_key": "verifications/photo.jpg",
  "conditions": [
    {
      "code": "C1",
      "description": "컵이 사진에 보여야 한다"
    },
    {
      "code": "C2",
      "description": "손이 컵을 잡고 있어야 한다"
    }
  ]
}
```

| 필드 | 의미 | 검사 |
|---|---|---|
| `ai_task_id` | 백엔드가 생성한 AI 작업 ID | 비어 있지 않은 문자열 |
| `verification_id` | 인증 시도 ID | 비어 있지 않은 문자열 |
| `image_key` | S3 객체 키 | 비어 있지 않은 문자열 |
| `conditions` | 판정할 조건 목록 | 비어 있으면 안 됨 |
| `conditions[].code` | 해당 도전 내 조건 구분 코드 | 요청 안에서 중복되면 안 됨 |
| `conditions[].description` | 자연어 판정 조건 | 비어 있으면 안 됨 |

조건 개수에 고정된 상한은 없다. 요청에 포함된 모든 조건을 판정하며, API 요청에
`required`, `condition_type`, DB ID, `sort_order`를 추가하지 않는다. 조건 코드와
요청 ID를 응답에서 그대로 돌려주므로 백엔드가 요청·응답 대응을 검증할 수 있다.

```bash
curl -X POST 'http://127.0.0.1:8000/internal/photo-verifications' \
  -H 'Content-Type: application/json' \
  --data '{"ai_task_id":"1","verification_id":"1","image_key":"verifications/photo.jpg","conditions":[{"code":"C1","description":"컵이 사진에 보여야 한다"},{"code":"C2","description":"손이 컵을 잡고 있어야 한다"}]}'
```

### 성공 응답

```json
{
  "ai_task_id": "1",
  "verification_id": "1",
  "processing_status": "SUCCEEDED",
  "checks": [
    {
      "code": "C1",
      "status": "MET",
      "reason": "사진에서 컵이 확인됩니다."
    },
    {
      "code": "C2",
      "status": "UNCERTAIN",
      "reason": "손이 컵을 잡고 있는 부분이 가려져 있습니다."
    }
  ],
  "model_version": "gemini-3.5-flash-lite"
}
```

- `checks`에는 요청 조건마다 결과가 정확히 하나씩 들어간다.
- `checks[].status`는 `MET`, `NOT_MET`, `UNCERTAIN` 중 하나다.
- `checks[].reason`은 조건별 판정 사유이며 최대 500자다.
- `model_version`은 AI 판정 파이프라인 버전이며 최대 50자다. 기본값은
  `photo-verifier-v1`이고 `AI_MODEL_VERSION`으로 배포 버전을 지정한다. 실제 공급자
  모델 ID는 서버의 `GEMINI_MODEL` 또는 `OLLAMA_MODEL` 설정으로 관리한다.
- 분석이 정상 완료됐다면 일부 조건이 `NOT_MET` 또는 `UNCERTAIN`이어도 HTTP 200이다.
- 백엔드는 `NOT_MET`이 하나라도 있으면 `FAILED`, 그렇지 않고 `UNCERTAIN`이 있으면
  `REVIEW_REQUIRED`, 모두 `MET`이면 `SUCCESS`로 판정한다. `NOT_MET`과
  `UNCERTAIN`이 함께 있으면 `FAILED`가 우선한다.

### 오류 응답

```json
{
  "ai_task_id": "1",
  "verification_id": "1",
  "processing_status": "ERROR",
  "error": {
    "code": "MODEL_UNAVAILABLE",
    "message": "현재 판정 모델을 사용할 수 없습니다."
  }
}
```

| HTTP | 코드 | 의미 |
|---:|---|---|
| 400 | `INVALID_REQUEST` | 요청 형식 또는 필수 값 오류 |
| 422 | `UNSUPPORTED_IMAGE` | 모델이 지원하지 않는 이미지 |
| 422 | `IMAGE_FETCH_FAILED` | S3 사진 조회 실패 |
| 500 | `INTERNAL_ERROR` | AI 서버 내부 오류 또는 스토리지 설정 오류 |
| 503 | `MODEL_UNAVAILABLE` | 모델 장애, 시간 초과, 설정 오류 또는 모델 응답 검증 실패 |

요청 형식 오류로 두 ID를 읽지 못하면 오류 응답에서 해당 ID는 `null`이다. 이미지
조회 실패나 모델 기술 오류는 사용자 인증 실패로 간주하지 않는다. 백엔드는 해당
요청을 일일 사용자 인증 횟수에서 제외하고, 기술적 재시도에는 같은 `ai_task_id`를
사용한다.

## 이미지 저장소 설정

운영 호출은 `image_key`를 S3 객체 키로 사용한다. 서버가 S3에서 사진을 임시 파일로
가져와 모델에 전달하고, 판정이 끝나면 임시 파일을 삭제한다. 파일 형식과 용량은
백엔드 업로드 경계에서 검사하며 AI 서버는 별도로 크기 제한을 적용하지 않는다.

```dotenv
AI_IMAGE_SOURCE=s3
S3_ACCESS_KEY_ID=...
S3_SECRET_ACCESS_KEY=...
AWS_REGION=ap-northeast-2
S3_BUCKET=moamu-s3-bucket
```

로컬 계약 테스트는 `AI_IMAGE_SOURCE=local`, `AI_IMAGE_ROOT=./data/images`를 설정하고
`image_key`에 해당 디렉터리 아래 상대 경로를 넣는다. 로컬 모드는 개발 테스트용이며
운영 환경은 S3를 사용한다.

## 판정 모델 입출력

Gemini 또는 Ollama 어댑터에는 이미지와 조건의 내부 순번, `code`, `description`이
전달된다. 모델 출력의 내부 순번을 검증한 뒤 요청 조건 코드에 다시 연결한다.
모델이 조건을 누락·중복하거나 요청 범위 밖의 결과를 내면 기술 오류로 처리하고
정상 인증 응답을 반환하지 않는다. 프롬프트의 기본 버전은
`photo-verification-v3`이며 각 버전은 `src/moamu_ai/prompt_versions/` 아래에서
독립 관리한다. v3는 판정 사유 반환을 추가한 API 계약 버전으로, 별도 실험을 통해
판정 정확도가 개선됐다고 주장하는 버전은 아니다.
