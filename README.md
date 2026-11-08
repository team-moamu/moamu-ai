# 모아뮤 AI 사진 인증 서비스

백엔드가 전달한 S3 사진과 도전 인증 조건을 Gemini 또는 로컬 Ollama 비전 모델로 판정하는 내부 FastAPI 서비스입니다. API 계약은 [AI 평가 문서의 API 계약](docs/ai-evaluation/api-contract.md)을 참고하세요.

## 담당 범위

- 백엔드는 사진 업로드, 이미지 형식·용량 검사, 인증 재시도와 최종 인증 상태 결정을 담당합니다.
- AI 서비스는 백엔드가 저장한 사진을 읽고 각 조건에 `MET`, `NOT_MET`, `UNCERTAIN` 판정과 사유를 반환합니다.
- AI 서비스는 전체 인증 성공·실패 상태를 계산하지 않습니다.

## 로컬 실행

저장소 루트에서 가상환경을 만들고 개발 의존성을 설치합니다.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
test -f .env || cp .env.example .env
```

Gemini와 S3를 사용할 경우 `.env`에 필요한 설정을 입력합니다. `.env`는 Git에 커밋하지 마세요.

```dotenv
AI_PROVIDER=gemini
AI_IMAGE_SOURCE=s3
AI_PROMPT_VERSION=photo-verification-v4
GEMINI_TOKEN_API_KEY=발급받은_Gemini_API_키
GEMINI_MODEL=gemini-3.5-flash-lite
AWS_REGION=ap-northeast-2
S3_BUCKET=moamu-s3-bucket
S3_ACCESS_KEY_ID=발급받은_S3_액세스_키
S3_SECRET_ACCESS_KEY=발급받은_S3_시크릿_키
```

서버 실행:

```bash
./run.sh
```

- 상태 확인: <http://127.0.0.1:8000/healthz>
- Swagger UI: <http://127.0.0.1:8000/docs>

설정 변수와 기본값은 [.env.example](.env.example)에 있습니다. 로컬 이미지로 테스트할 때는 `AI_IMAGE_SOURCE=local`과 `AI_IMAGE_ROOT=./data/images`를 설정합니다.

## 사진 판정 API

`POST /internal/photo-verifications`는 백엔드가 생성한 AI 작업 ID, 인증 시도 ID, S3 객체 키, 조건 코드와 설명을 받습니다. 이미지 경로 대신 S3 객체 키를 보냅니다.

```bash
curl --request POST \
  --url 'http://127.0.0.1:8000/internal/photo-verifications' \
  --header 'Content-Type: application/json' \
  --data-binary @- <<'JSON'
{
  "ai_task_id": "local-test-task-1",
  "verification_id": "local-test-verification-1",
  "image_key": "artworks/girl_with_pearl_earring_studying.png",
  "conditions": [
    {"code": "C1", "description": "책 또는 학습 노트가 사진에 보여야 한다"},
    {"code": "C2", "description": "직접 작성한 학습 메모가 사진에서 식별되어야 한다"}
  ]
}
JSON
```

성공하면 요청의 ID와 조건 코드에 대응하는 결과를 반환합니다.

```json
{
  "ai_task_id": "local-test-task-1",
  "verification_id": "local-test-verification-1",
  "processing_status": "SUCCEEDED",
  "checks": [
    {"code": "C1", "status": "MET", "reason": "책이 확인됩니다."},
    {"code": "C2", "status": "UNCERTAIN", "reason": "필기 내용이 선명하게 보이지 않습니다."}
  ],
  "model_version": "photo-verifier-v1"
}
```

실제 API 입력과 오류 형식은 [API 계약 문서](docs/ai-evaluation/api-contract.md)에 정리되어 있습니다. `test.sh`는 기본 테스트 이미지 키와 학습 조건으로 요청을 보냅니다. 다른 이미지를 시험하려면 객체 키를 첫 번째 인자로 전달합니다.

```bash
./test.sh 'artworks/girl_with_pearl_earring_studying.png'
```

## 모델과 프롬프트 설정

Gemini API는 `AI_PROVIDER=gemini`, `GEMINI_TOKEN_API_KEY`, `GEMINI_MODEL`을 설정합니다. 프롬프트는 `photo-verification-v1`부터 `photo-verification-v4`까지 선택할 수 있으며 기본값은 v4입니다. 모델 비교 시 `GEMINI_THINKING_LEVEL`을 지정해 추론 수준을 고정할 수 있습니다.

CPU 기반 로컬 Ollama 비전 모델은 `AI_PROVIDER=ollama`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL`을 설정합니다. Ollama 서버와 모델은 별도로 준비해야 합니다.

```dotenv
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen3-vl:2b
```

각 프롬프트 원문은 [`src/moamu_ai/prompt_versions/`](src/moamu_ai/prompt_versions/) 아래 버전별 파일에 보존합니다. `.env`의 `AI_PROMPT_VERSION`으로 서버 기본 버전을 선택하고, 벤치마크에서는 `--prompt-version`으로 따로 지정할 수 있습니다.

## 오프라인 평가

단위 테스트는 가짜 모델을 사용합니다. 테스트와 벤치마크 절차 및 데이터 기록은 [AI 평가 문서](docs/ai-evaluation/)를 참고하세요.

평가 명령은 기본적으로 미리보기 모드이며 모델 API를 호출하지 않습니다. 실제 모델 호출을 요청할 때만 `--execute`를 추가합니다. Gemini는 한 번에 최대 6개 이미지 사례까지 실행합니다.

```bash
moamu-evaluate --manifest data/evaluation/open-images-v7-smoke.jsonl --provider gemini --limit 6 --prompt-version photo-verification-v2
moamu-evaluate --manifest data/evaluation/open-images-v7-smoke.jsonl --provider gemini --limit 6 --prompt-version photo-verification-v2 --execute
```

실행 결과는 기본적으로 `data/evaluation/results/`에 저장되며 Git에는 포함하지 않습니다. 이미지 파일은 `AI_IMAGE_ROOT` 아래에 준비합니다. 데이터 출처, 라이선스, 라벨과 지표는 각 매니페스트와 평가 문서에 기록합니다.

## 프로젝트 구조

```text
src/moamu_ai/                  FastAPI 앱, 요청 검증, 판정 서비스, 저장소·모델 어댑터
src/moamu_ai/prompt_versions/  버전별 고정 프롬프트
tests/                         API·스키마·모델 어댑터·평가 검증
data/evaluation/               평가용 JSONL 매니페스트
docs/ai-evaluation/            모델, 프롬프트, 데이터셋, API 계약 기록
```
