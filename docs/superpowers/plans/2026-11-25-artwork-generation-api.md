# 명화 생성 비동기 API 구현 계획

> **실행 방식:** 현재 저장소에서 순서대로 직접 구현한다. 각 작업은 독립적으로 검증하고 작은 커밋으로 나눈다.

**목표:** 설계서의 생성 접수·상태 조회 API를 구현해 Spring이 작업을 접수하고 결과를 조회할 수 있게 한다.

**구조:** FastAPI는 SQLite 파일에 작업 본문과 상태를 먼저 저장한 뒤 `202 PENDING`을 반환한다. 단일 프로세스의 백그라운드 워커가 저장된 대기 작업을 재개하고, 권리 확인 카탈로그·Gemini 편집기·비공개 S3를 이용해 최종 상태를 저장한다.

**기술:** FastAPI, 표준 라이브러리 `sqlite3`, 기존 Gemini·boto3 어댑터, pytest.

**기준 명세:**
- `assets/v261123/이미지 생성 접수 41fbfd0eb45080cb8bdfc40f00b0e469.md`
- `assets/v261123/이미지 생성 상태 조회 41fbfd0eb450801481e2fdd61d069de1.md`
- `assets/v261123/MOAMU 3차 MVP 자유목표 AI 명화 생성 연동 설계서 41dbfd0eb4508020ba74e0acc6011b8f.md`

## 공통 제약

- 접수 경로는 `POST /internal/artwork-generations`, 상태 조회 경로는 `GET /internal/artwork-generations/{taskId}/versions/{taskVersion}`이다.
- 새 작업은 저장을 마친 뒤 HTTP `202`와 `PENDING`을 반환한다. 같은 키·같은 본문은 기존 작업을 반환하고, 같은 키·다른 본문은 HTTP `409`다.
- 접수 당시 이미 만료된 새 요청은 거부한다. 조회 결과는 `PENDING`, `RUNNING`, `SUCCEEDED`, `FAILED` 중 하나다.
- 이미지 결과는 비공개 S3에 작업 ID와 버전으로 구분해 저장한다. 응답에는 객체 키, MIME, 크기, SHA-256, 원본 출처와 `reuseAllowed`를 포함한다.
- 이미지 모델 호출은 자동 재시도하지 않는다. Spring이 새 `taskVersion`으로 명시적 재시도를 시작한다.
- 내부 API 인증은 Bearer 토큰으로 구현하고 `AI_INTERNAL_API_TOKEN` 환경 변수에 둔다.
- SQLite 파일은 재시작 복구용 영속 저장소다. MVP 운영은 영속 볼륨을 연결한 단일 FastAPI 프로세스로 제한한다.

## 검토할 실패 사례

- 같은 작업 키를 동시에 두 번 접수해도 모델 호출은 한 번만 발생한다.
- 같은 키에 다른 본문이 오면 기존 결과를 돌려주지 않고 `409`를 반환한다.
- 접수 뒤 만료되거나 모델·S3가 실패하면 `FAILED`와 기계 판독 가능한 `errorCode`, `retryable`을 반환한다.
- 프로세스 재시작 뒤 `RUNNING` 작업을 복구하며, 성공 상태는 같은 이미지 메타데이터를 유지한다.
- 인증 토큰이 없거나 설정되지 않은 경우 내부 엔드포인트가 공개되지 않는다.

## 작업

### 1. 영속 작업 저장소

**파일:** 새 `src/moamu_ai/artwork_task_store.py`, 새 `tests/test_artwork_task_store.py`, 수정 `src/moamu_ai/config.py`.

- [ ] 멱등성 키 `(taskId, taskVersion)`, 정규화 본문 해시, 상태 및 결과를 보관하는 SQLite 테이블을 구현한다.
- [ ] 동일 본문 재접수·본문 충돌·원자적 `PENDING → RUNNING`·완료·실패·재시작 복구 테스트를 추가한다.
- [ ] DB 파일 경로 설정 기본값과 부모 디렉터리 생성을 구현한다.

### 2. 생성 처리와 S3 결과 저장

**파일:** 새 `src/moamu_ai/artwork_generation_service.py`, 수정 `src/moamu_ai/image_sources.py`, 새 `tests/test_artwork_generation_service.py`.

- [ ] 작업 ID·버전에 따라 카탈로그 원본을 결정하고, Gemini 편집 결과를 검사한다.
- [ ] S3에 같은 작업 버전의 결과를 저장하고 크기·MIME·SHA-256·원본 권리 정보를 결과로 만든다.
- [ ] S3와 Gemini는 가짜 어댑터로 대체해 성공·기한 만료·실패·재개 경로를 검증한다.

### 3. FastAPI 접수·조회와 워커

**파일:** 수정 `src/moamu_ai/app.py`, `src/moamu_ai/config.py`, `tests/test_api.py` 또는 새 `tests/test_artwork_generation_api.py`.

- [ ] Bearer 인증, 명세된 `202` 접수, 중복·충돌 처리, 버전 조회 응답을 라우트로 연결한다.
- [ ] 서버 시작 시 저장된 미완료 작업을 다시 예약하고, 새 작업은 DB 기록 후 백그라운드에서 처리한다.
- [ ] 권한 오류·만료 요청·없는 작업·모든 상태별 API 응답을 테스트한다.

### 4. 실행 안내와 검증

**파일:** 수정 `.env.example`, `README.md`.

- [ ] `AI_INTERNAL_API_TOKEN`과 영속 DB 경로 설정, 로컬 단일 프로세스 제약을 안내한다.
- [ ] 명세와 같은 POST/GET curl 예시를 기록한다.
- [ ] 전체 테스트와 lint를 실행하고 변경분을 검토한다.

## 위험과 완화

| 위험 | 영향 | 완화 |
|---|---|---|
| 컨테이너 임시 파일 시스템에 SQLite를 저장 | 재시작·배포 후 작업 기록 소실 | `AI_ARTWORK_TASK_DB_PATH`를 영속 볼륨에 설정하도록 문서화 |
| 여러 FastAPI 프로세스가 같은 SQLite 작업 큐를 사용 | 실행 선점·재시작 복구 경쟁 | MVP는 단일 프로세스로 제한하고 이후 공유 큐/DB로 옮길 경계 명시 |
| 모델 완료 후 S3 업로드·상태 저장 중 프로세스 종료 | 결과 재생성 또는 미확정 객체 발생 | 작업 버전별 고정 객체 키와 성공 결과 영속화, 시작 시 복구 처리 |
| 동기 외부 호출이 워커를 오래 점유 | 요청 만료 초과 | 모델 제한 시간을 설정하고 작업 기한을 매 단계 확인 |
