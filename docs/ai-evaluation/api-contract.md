# 내부 AI API 계약

## `POST /internal/goals/evaluate-verifiability`

자유목표가 사진으로 인증 가능한지 판단하고, 인증 조건·촬영 가이드·판정 범위와
분류 후보 또는 대안 목표를 반환하는 내부 API다. `categoryPath`는 필수 필드이며,
기존 분류 경로를 재사용할 때는 대·중·소 분류명을 전달하고 신규 분류 후보가
필요하면 `null`을 전달한다. 분석 결과는 AI 모델이 만들며 카테고리 DB 조회·저장,
Redis 보관과 목표 확정은 백엔드가 담당한다.

### 요청

```json
{
  "goal": "매일 영어 뉴스 10분 듣고 새로 들은 표현 적기",
  "categoryPath": null
}
```

### 성공 응답: 사진 인증 가능

```json
{
  "status": "VERIFIABLE",
  "goal": "매일 영어 뉴스 10분 듣고 새로 들은 표현 적기",
  "normalizedGoal": "매일 영어 뉴스에서 들은 표현 기록하기",
  "proposedCategoryPath": {
    "major": "학습",
    "middle": "외국어",
    "minor": "듣기 학습"
  },
  "conditions": [
    "영어 뉴스에서 들은 표현을 기록한 학습 흔적이 사진에서 확인되어야 합니다."
  ],
  "photoGuide": "기록한 표현이 읽히도록 노트나 학습 기록을 촬영해 주세요.",
  "verificationScope": "사진에 남은 표현 기록을 확인합니다. 실제 청취 시간은 판정 범위에서 제외합니다.",
  "alternatives": []
}
```

### 성공 응답: 사진 인증 어려움

`NOT_VERIFIABLE`은 정상 판정이며 HTTP 200으로 반환한다. 대안 목표를 정확히 세 개
포함한다.

```json
{
  "status": "NOT_VERIFIABLE",
  "goal": "매일 감사한 마음 갖기",
  "normalizedGoal": null,
  "proposedCategoryPath": null,
  "conditions": [],
  "photoGuide": null,
  "verificationScope": null,
  "alternatives": [
    "오늘 감사한 일 한 가지 적기",
    "고마웠던 순간을 일기에 기록하기",
    "감사한 사람에게 전할 문장 써보기"
  ]
}
```

### 요청·응답 규칙

| 필드 | 규칙 |
|---|---|
| `goal` | 공백이 아닌 사용자 원문 |
| `categoryPath` | 필수. `null` 또는 `major`, `middle`, `minor`가 모두 있는 객체 |
| `normalizedGoal` | `VERIFIABLE`에서 공백이 아닌 정리 목표. `NOT_VERIFIABLE`에서는 `null` |
| `proposedCategoryPath` | 입력 경로가 `null`인 인증 가능 결과에서만 제안 객체. 기존 경로를 입력하면 `null` |
| `conditions` | 인증 가능 결과에 한 개 이상, 각 최대 300자. 인증 불가 결과에서는 빈 배열 |
| `photoGuide` | 인증 가능 결과에서 최대 500자. 인증 불가 결과에서는 `null` |
| `verificationScope` | 인증 가능 결과에서 최대 1,000자. 인증 불가 결과에서는 `null` |
| `alternatives` | 인증 가능 결과에서는 빈 배열. 인증 불가 결과에서는 사진으로 확인 가능한 목표 세 개 |

```bash
curl --request POST \
  --url 'http://127.0.0.1:8000/internal/goals/evaluate-verifiability' \
  --header 'Content-Type: application/json' \
  --data '{"goal":"매일 영어 뉴스 10분 듣고 새 표현 적기","categoryPath":null}'
```

### 오류 응답

400 요청 오류 응답 예시:

```json
{
  "code": "INVALID_REQUEST",
  "message": "요청이 올바르지 않습니다."
}
```

| HTTP | 코드 | 의미 |
|---:|---|---|
| 400 | `INVALID_REQUEST` | JSON 형식, 목표 문장 또는 필수 `categoryPath`가 유효하지 않음 |
| 500 | `INTERNAL_SERVER_ERROR` | 모델 공급자 장애 이외의 내부 처리 오류 |
| 503 | `AI_MODEL_UNAVAILABLE` | 모델 설정·호출 오류 또는 모델 응답 계약 위반 |

목표 분석용 프롬프트는 `src/moamu_ai/goal_prompt_versions/` 아래 버전별로 관리하며,
`.env`의 `AI_GOAL_PROMPT_VERSION`으로 선택한다. 공급자는 기존 `AI_PROVIDER` 설정을
공유하므로 Gemini와 Ollama 중 하나를 지정한다. 이 API는 목표 텍스트만 모델에 전달하고
이미지를 보내지 않는다.

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
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
# 임시 자격 증명을 사용하는 경우에만 설정
AWS_SESSION_TOKEN=...
AWS_REGION=ap-northeast-2
S3_BUCKET=moamu-s3-bucket
```

기존 `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_SESSION_TOKEN` 이름도 호환됩니다.
AWS 표준 이름과 기존 S3 이름 중 한 종류만 설정하세요. IAM 역할을 사용하는 환경에서는
액세스 키 설정을 생략할 수 있습니다.

로컬 계약 테스트는 `AI_IMAGE_SOURCE=local`, `AI_IMAGE_ROOT=./data/images`를 설정하고
`image_key`에 해당 디렉터리 아래 상대 경로를 넣는다. 로컬 모드는 개발 테스트용이며
운영 환경은 S3를 사용한다.

## 판정 모델 입출력

Gemini 또는 Ollama 어댑터에는 이미지와 조건의 내부 순번, `code`, `description`이
전달된다. 모델 출력의 내부 순번을 검증한 뒤 요청 조건 코드에 다시 연결한다.
모델이 조건을 누락·중복하거나 요청 범위 밖의 결과를 내면 기술 오류로 처리하고
정상 인증 응답을 반환하지 않는다. 모델 입력에는 내부 조건 순번과 자연어 설명을
직렬화하며, 요청 코드는 결과를 백엔드 요청 순서에 다시 연결하는 데 사용한다.
프롬프트의 기본 버전은 `photo-verification-v4`이며 각 버전은
`src/moamu_ai/prompt_versions/` 아래에서 독립 관리한다. 벤치마크 CLI는
`--prompt-version`으로 별도 버전을 선택할 수 있다. 모델 응답 스키마는 조건별
판정 사유를 요구하고, API는 이를 `checks[].reason`으로 반환한다.
