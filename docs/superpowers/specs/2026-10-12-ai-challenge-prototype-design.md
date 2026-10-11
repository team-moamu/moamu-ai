# MOAMU AI Challenge Prototype Design

## 1. 목적

MOAMU의 AI 엔지니어링 흐름을 검증하는 로컬 Python 프로토타입을 만든다. 프로토타입은 다음 두 기능을 제공한다.

1. 사용자가 입력한 20자 이내 목표를 사진 인증 가능한 도전으로 설계한다.
2. 사용자가 제출한 이미지가 도전 생성 시 확정된 필수 인증 조건을 충족하는지 판정한다.

Gemini API를 실제로 호출하는 Adapter를 제공하되 모델 호출부는 교체 가능한 인터페이스로 분리한다. 일반 단위 테스트에서는 결정론적인 Fake 구현을 사용하고, 명시적으로 활성화한 통합 테스트만 실제 API를 호출한다. 이미지 생성은 구현 범위에서 제외한다.

## 2. 기술 범위

- Python 3.11 이상
- Pydantic 2.x: 입출력 스키마와 검증
- pytest: 단위 테스트
- Pillow: 이미지 파일의 형식, 크기, 손상 여부 검증
- google-genai: Gemini API 호출
- python-dotenv: 로컬 개발 환경의 `.env` 탐색 및 로딩
- FastAPI는 이번 프로토타입에 포함하지 않는다.

기본 모델은 `gemini-3.1-flash-lite`로 하고 OpenAI 대안은 `gpt-5.6-luna`로 둔다. 모델 ID는 도메인 로직에 하드코딩하지 않고 설정과 Provider Adapter에 둔다.

## 3. 시스템 경계

프로토타입은 네 부분으로 나눈다.

- 도메인 스키마: 도전 설계, 인증 조건, 이미지 판정 결과를 표현한다.
- 도전 설계 서비스: 사용자 목표를 검증하고 모델용 요청을 만든 뒤 응답을 검증한다.
- 이미지 인증 서비스: 이미지 파일을 검증하고 확정된 조건을 기준으로 조건별 결과와 최종 결과를 계산한다.
- 모델 포트와 Fake 구현: 단위 테스트에서 예상 모델 응답을 주입한다.
- Gemini Adapter: 공식 SDK로 구조화된 도전 계획과 조건별 이미지 판정을 요청한다.

서비스는 공급자 이름이나 SDK 객체를 알지 못한다. 따라서 이후 Gemini 또는 OpenAI Adapter를 추가해도 도메인 스키마와 판정 규칙은 바뀌지 않는다.

## 4. 함수 1: 도전 설계

### 인터페이스

```python
def generate_challenge(goal_text: str, model: ChallengeModel) -> ChallengePlan:
    ...
```

### 입력 규칙

- 앞뒤 공백을 제거한 목표가 1자 이상이어야 한다.
- Python 문자열 길이 기준으로 20자 이하여야 한다.
- 공백뿐인 문자열과 20자를 초과한 문자열은 모델 호출 전에 거절한다.

### 인증 가능성

`verifiability`는 다음 중 하나다.

- `VERIFIABLE`: 목표를 사진에서 직접 확인할 수 있다.
- `SUBSTITUTE`: 원래 목표 자체는 확인할 수 없지만 사진으로 확인 가능한 대체 행동을 제안할 수 있다.
- `NOT_VERIFIABLE`: 직접 조건과 정직한 대체 조건을 모두 만들 수 없다.
- `UNSUPPORTED`: 서비스의 조건 유형으로 지원하기 어렵다.
- `REJECTED`: 위험하거나 부적절한 목표다.

`SUBSTITUTE`에서는 원래 목표를 달성했다고 주장하지 않는다. 예를 들어 "금연하기"에는 "흡연 대신 산책한 기록 남기기" 같은 대체 행동과, 이것이 금연 자체를 증명하지 않는다는 한계를 함께 반환한다.

`NOT_VERIFIABLE`, `UNSUPPORTED`, `REJECTED`는 정상적인 도전 계획처럼 저장할 수 없다. 이유와 수정 안내를 반환하고 필수 조건 및 촬영 가이드는 비운다.

### 성공 출력

`VERIFIABLE` 또는 `SUBSTITUTE` 결과는 다음을 만족해야 한다.

- `challenge_name`: 화면에 표시할 간결한 도전명
- `required_conditions`: 최소 2개, 최대 4개
- `shooting_guides`: 정확히 3개
- `verification_scope`: 사진으로 확인하는 범위
- `limitation`: 사진만으로 확인할 수 없는 내용
- `substitute_action`: `SUBSTITUTE`일 때만 필수

각 필수 조건은 고유한 `condition_id`, 조건 유형, 사진에서 관찰 가능한 문장을 가진다. 허용하는 조건 유형은 다음과 같다.

- `OBJECT_PRESENT`
- `ACTIVITY_IN_PROGRESS`
- `HANDWRITTEN_RECORD`
- `SCREEN_RECORD`
- `RESULT_OUTPUT`
- `PLACE`

`DATE_VISIBLE`은 PRD에 따라 보조 조건 전용이므로 필수 조건에 사용할 수 없다. 시간 지속, 하루 전체 행동, 감정이나 의지처럼 한 장의 사진에서 확인할 수 없는 내용을 필수 조건으로 만들 수 없다.

## 5. 함수 2: 이미지 인증

### 인터페이스

```python
def verify_challenge(
    image_path: Path,
    required_conditions: list[VerificationCondition],
    model: VerificationModel,
) -> VerificationResult:
    ...
```

### 이미지 사전 검증

모델을 사용하기 전에 다음을 확인한다.

- 파일이 존재하고 일반 파일이어야 한다.
- 허용 형식은 JPEG, PNG, WEBP다.
- 파일 크기는 10MB 이하여야 한다.
- Pillow로 열고 검증했을 때 손상된 이미지가 아니어야 한다.
- 이미지 가로와 세로가 각각 256픽셀 이상이어야 한다.

검증 실패는 사용자의 인증 실패가 아니라 입력 오류로 처리하고 예외를 반환한다.

### 조건별 판정

모델은 각 필수 조건을 다음 중 하나로 판정한다.

- `MET`: 사진에서 조건 충족이 확인된다.
- `NOT_MET`: 사진에서 조건이 충족되지 않았음이 확인된다.
- `UNCERTAIN`: 가림, 흐림, 프레임 이탈 등으로 판단하기 어렵다.

각 판정에는 간결한 `reason`과 사진에서 확인한 `evidence`를 포함한다. 모델이 요청받지 않은 조건을 추가하거나 일부 조건을 누락하면 응답 검증 오류로 처리한다.

### 최종 결과

- 모든 필수 조건이 `MET`이면 `SATISFIED`다.
- 하나라도 `NOT_MET` 또는 `UNCERTAIN`이면 외부 결과는 `UNSATISFIED`다.
- `UNCERTAIN`이 포함된 경우 `retry_recommended=True`로 반환해 재촬영 안내에 사용할 수 있게 한다.

외부의 이진 결과와 별개로 조건별 상태는 보존한다. 이는 PRD와 SVG의 조건별 근거 및 재촬영 화면을 지원하고, 추후 `REVIEW_REQUIRED` 운영 정책을 도입할 수 있게 한다.

## 6. 모델 포트

두 역할을 별도 Protocol로 정의한다.

```python
class ChallengeModel(Protocol):
    def generate(self, request: ChallengeModelRequest) -> ChallengeModelResponse: ...

class VerificationModel(Protocol):
    def verify(self, request: VerificationModelRequest) -> VerificationModelResponse: ...
```

테스트용 Fake는 입력별 응답을 미리 등록하며 호출 횟수와 마지막 요청을 기록한다. 서비스 테스트는 이를 통해 모델 호출 전 입력 거절, 요청 변환, 응답 검증, 최종 결과 계산을 독립적으로 검증한다.

Gemini Adapter는 동일한 Pydantic 스키마를 JSON Schema 기반 구조화 출력으로 사용한다. 이미지 판정은 검증된 이미지 바이트를 inline 입력으로 전송하며, 10MB 제한은 Gemini의 20MB inline 요청 한도 안에 머물게 한다. API 키는 `GEMINI_API_KEY` 환경변수에서 읽고, 로컬 실행 시 현재 디렉터리부터 상위 디렉터리 방향으로 `.env`를 탐색한다. 키 값은 로그, 예외 메시지, 프론트엔드 또는 저장소에 포함하지 않는다.

실제 API 통합 테스트는 `RUN_GEMINI_INTEGRATION=1`일 때만 실행한다. 통합 테스트 이미지는 테스트가 로컬에서 생성한 합성 이미지만 사용하며 사용자 사진이나 `assets` 파일을 전송하지 않는다.

## 7. 오류 처리

다음 오류를 구분한다.

- `InvalidGoalError`: 빈 목표 또는 20자 초과
- `InvalidChallengePlanError`: 조건 개수, 촬영 가이드 개수, 유형, 대체 행동 등 모델 응답 규칙 위반
- `InvalidImageError`: 파일 없음, 미지원 형식, 과대·저해상도·손상 이미지
- `InvalidVerificationResponseError`: 조건 누락, 중복, 알 수 없는 조건 ID
- `ModelConfigurationError`: API 키 누락 또는 잘못된 모델 설정
- `ModelInvocationError`: Gemini 요청 실패, 거절, 빈 응답 또는 구조화 응답 파싱 실패

Gemini 네트워크 오류는 사용자의 도전 실패나 인증 실패로 변환하지 않는다. `ModelInvocationError`로 구분하며 현재 프로토타입에서는 SDK 호출을 내부적으로 재시도하지 않는다.

## 8. 테스트 전략

### 도전 설계

- 정상적인 직접 인증 목표가 조건 2개 이상과 가이드 3개를 반환한다.
- 공백 입력과 21자 입력은 모델을 호출하지 않고 실패한다.
- `SUBSTITUTE` 결과에는 대체 행동과 인증 한계가 반드시 있다.
- 직접 관찰 불가능한 조건 또는 필수 `DATE_VISIBLE`을 거절한다.
- 조건 ID 중복, 조건 1개, 가이드 2개·4개를 거절한다.
- 거절 계열 결과에는 도전용 조건이 없어야 한다.

### 이미지 인증

- 모든 조건이 `MET`이면 `SATISFIED`다.
- 하나라도 `NOT_MET`이면 `UNSATISFIED`다.
- 하나라도 `UNCERTAIN`이면 `UNSATISFIED`이며 재촬영을 권장한다.
- 조건 누락, 추가, 중복 판정을 거절한다.
- 존재하지 않는 파일, 텍스트 위장 파일, 손상 이미지, 10MB 초과 이미지, 저해상도 이미지를 거절한다.
- 입력 이미지 오류에서는 모델을 호출하지 않는다.

### Gemini 통합

- 키가 없으면 Adapter 생성 또는 호출이 명확한 설정 오류로 실패한다.
- 도전 생성 통합 테스트는 20자 이내 목표로 스키마에 맞는 결과를 받는다.
- 이미지 판정 통합 테스트는 생성한 합성 이미지를 전송해 모든 요청·응답 필드를 파싱할 수 있는지 확인한다.
- 통합 테스트는 기본 pytest 실행에서는 건너뛰고 명시적 환경변수로만 활성화한다.

## 9. 제외 범위

- 결제 설정 자동화
- FastAPI 엔드포인트
- S3 업로드와 데이터베이스 저장
- 이미지 생성
- 중복 사진 탐지
- 운영자 검토와 자동 재처리

OpenAI Adapter, FastAPI, 저장소 연동과 이미지 생성은 프로토타입의 스키마와 테스트 결과가 승인된 후 별도 단계로 추가한다.
