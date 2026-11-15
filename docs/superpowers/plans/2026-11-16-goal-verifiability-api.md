# 자유목표 사진 인증 가능 여부 API 구현 계획

> **실행 방식:** 이 계획을 기준으로 현재 세션에서 단계별 구현한다.

**목표:** `POST /internal/goals/evaluate-verifiability`를 구현해 자유목표의 사진 인증 가능 여부와 인증 조건·촬영 가이드·판정 범위·필요한 분류 후보 또는 대안 목표를 반환한다.

**구조:** 입력·모델 출력·내부 API 응답을 Pydantic 스키마로 분리한다. 사진 인증 판정기와 별도의 목표 분석 프롬프트 및 모델 분석기를 두고, 기존 `AI_PROVIDER` 선택에 따라 Gemini 또는 Ollama를 사용한다. 서비스 계층은 상태별 필드와 요청 카테고리 경로에 따른 후보 반환 규칙을 검증한다.

**기술:** FastAPI, Pydantic v2, Gemini SDK, Ollama HTTP API, pytest.

**기준 문서:** `assets/v261115/`의 2차 MVP 설계서, 사진 인증 가능 여부 API 명세, 자유목표 분석 API 명세.

## 범위

- 내부 API 경로는 `/internal/goals/evaluate-verifiability`로 한다.
- 계약의 JSON 필드는 camelCase로 직렬화한다. 입력은 `goal`, 필수 nullable `categoryPath`를 받는다.
- API 응답은 입력 원문 `goal`, 모델 정리 목표 `normalizedGoal`, 판정 상태, 조건, 촬영 가이드, 인증 범위, 분류 후보, 대안을 포함한다.
- `NOT_VERIFIABLE`은 정상 응답이며 대안 목표를 정확히 3개 반환한다.
- DB 카테고리 탐색, Redis 결과 저장, 외부 `/api/goals/analyze`, 도전 확정은 백엔드 범위다.
- 실제 Gemini/Ollama 호출은 개발 검증에서 실행하지 않는다. 공급자는 테스트 대역으로 검증한다.

## 구현 단계

1. 요청·출력·API 오류 스키마와 상태별 검증을 추가하고 스키마 테스트를 작성한다.
2. 목표 분석 프롬프트를 별도 버전 파일로 보관하고 Gemini/Ollama 텍스트 분석기와 팩토리 테스트를 추가한다.
3. 서비스에서 모델 응답과 입력 경로의 일관성을 검증하고 FastAPI 엔드포인트·오류 매핑 테스트를 추가한다.
4. 내부 API 계약 문서와 실행 설정 예시를 갱신하고 전체 테스트·정적 검사를 실행한다.

## 리뷰 초점

- `categoryPath`가 누락된 경우와 명시적 `null`인 경우를 구분한다.
- `VERIFIABLE`과 `NOT_VERIFIABLE`에서 필드 조합 및 대안 개수를 엄격히 확인한다.
- 기존 분류 경로가 입력되면 제안 경로를 반환하지 않고, 경로가 `null`이면 인증 가능한 결과에만 제안 경로를 요구한다.
- 목표 문자열의 지시문 삽입을 모델 지시문으로 취급하지 않도록 프롬프트에서 사용자 입력을 데이터로 제한한다.
- 기존 `/internal/photo-verifications`의 오류 계약과 동작을 유지한다.
