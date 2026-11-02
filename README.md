# 모아뮤 AI 사진 인증 서비스

백엔드가 전달한 사진 경로와 도전 인증 조건을 바탕으로, 사진이 각 조건을 충족하는지 판정하는 내부 FastAPI 서비스입니다. Gemini API 또는 로컬 Ollama 비전 모델을 사용할 수 있습니다.

## 담당 범위

- 백엔드가 활성 도전의 인증 조건과 사진 경로를 전달합니다.
- AI 서비스는 조건별 `MET`(충족), `NOT_MET`(미충족), `UNCERTAIN`(판정 불가)을 반환합니다.
- 인증 결과를 전체 성공·실패 상태로 합치는 일, 사진 업로드와 파일 형식·용량 검사는 백엔드 담당입니다.
- 현재 사진은 AI 서비스가 접근할 수 있는 로컬 경로에서 읽습니다. S3 객체를 직접 읽는 기능은 아직 연결되어 있지 않으며, `.env`의 S3 설정값도 현재 서비스에서 사용하지 않습니다.

## 로컬 실행

저장소 루트에서 가상환경을 만들고 개발 의존성을 설치합니다.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

`.env`가 없을 때만 예시 파일을 복사합니다. 기존 `.env`를 덮어쓰지 마세요.

```bash
test -f .env || cp .env.example .env
```

`.env`에서 사용할 모델과 이미지 루트를 설정한 뒤 서버를 실행합니다.

```dotenv
AI_PROVIDER=gemini
AI_IMAGE_ROOT=./data/images
AI_PROMPT_VERSION=photo-verification-v4
GEMINI_TOKEN_API_KEY=발급받은_Gemini_API_키
GEMINI_MODEL=gemini-3.5-flash-lite
```

```bash
uvicorn moamu_ai.app:app --reload --host 127.0.0.1 --port 8000
```

- 상태 확인: <http://127.0.0.1:8000/healthz>
- Swagger UI: <http://127.0.0.1:8000/docs>

`.env`에는 비밀키가 들어가므로 Git에 커밋하지 마세요. 변수 전체 목록과 기본값은 [.env.example](.env.example)을 참고하세요.

## 사진 판정 API

`POST /internal/photo-verifications`에 사진 경로와 백엔드가 저장한 활성 도전 조건 스냅샷을 전달합니다. `image_path`는 `AI_IMAGE_ROOT` 아래에 실제로 존재하고 AI 서비스에서 읽을 수 있어야 합니다.

```bash
curl --request POST \
  --url 'http://127.0.0.1:8000/internal/photo-verifications' \
  --header 'Content-Type: application/json' \
  --data-binary @- <<'JSON'
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
    }
  ]
}
JSON
```

예시의 ID는 임의 값입니다. 실제 요청에는 활성 도전의 `challenge_condition_id`를 사용해야 합니다. 템플릿의 `goal_template_condition_id`와는 다른 ID입니다.

조건은 2~5개를 받을 수 있으며, 그중 필수 조건이 최소 2개여야 합니다. `required`는 필수 조건이면 `"Y"`, 선택 조건이면 `"N"`입니다. 결과는 조건별로 반환하며, 전체 성공 여부는 백엔드가 계산합니다.

```json
{
  "results": [
    {"challenge_condition_id": 301, "status": "MET"},
    {"challenge_condition_id": 302, "status": "UNCERTAIN"}
  ]
}
```

`code`, `condition_type`, `required`, `sort_order`는 백엔드가 관리하는 조건 정보입니다. 모델은 조건 ID와 자연어 설명을 기준으로 판정합니다. 요청·응답 규칙과 오류 코드는 [API 계약 문서](docs/ai-evaluation/api-contract.md)를 참고하세요.

## 모델 설정

### Gemini API

`.env`에서 `AI_PROVIDER=gemini`를 선택하고 `GEMINI_TOKEN_API_KEY`, `GEMINI_MODEL`, `AI_PROMPT_VERSION`을 설정합니다. 프롬프트 버전은 `photo-verification-v1`부터 `photo-verification-v4`까지 선택할 수 있으며, 기본값은 v4입니다. 모델 비교를 할 때는 `GEMINI_THINKING_LEVEL=low`로 설정해 추론 수준을 맞출 수 있습니다. 생략하면 각 모델의 기본값을 사용합니다. 기본 설정은 [.env.example](.env.example)에 있습니다.

### Ollama

로컬 Ollama 비전 모델을 사용할 때는 다음처럼 설정합니다. Ollama 서버와 지정한 모델은 별도로 준비해야 합니다.

```dotenv
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen3-vl:2b
```

## 테스트와 오프라인 평가

단위 테스트는 실제 Gemini API를 호출하지 않도록 가짜 모델을 사용합니다.

```bash
pytest
```

평가 명령은 기본적으로 실행 계획만 검증합니다. 실제 Gemini 호출을 하려면 `--execute`를 추가해야 하며, 한 번 실행할 때 이미지 사례는 최대 6개로 제한됩니다.

```bash
moamu-evaluate --manifest data/evaluation/open-images-v7-smoke.jsonl --provider gemini --limit 6 --prompt-version photo-verification-v2
moamu-evaluate --manifest data/evaluation/open-images-v7-smoke.jsonl --provider gemini --limit 6 --prompt-version photo-verification-v2 --execute
```

벤치마크의 `--prompt-version`은 `.env`의 `AI_PROMPT_VERSION`보다 우선합니다. 실행 결과에는 실제 사용한 프롬프트 버전과 해시가 기록됩니다.

이미지는 `AI_IMAGE_ROOT` 아래에 준비하고, 평가 데이터와 모델·프롬프트 기록은 [AI 평가 문서](docs/ai-evaluation/README.md)에서 확인하세요. 실행 결과 디렉터리는 Git에 저장하지 않습니다.

Open Images 외의 데이터 출처를 추가하고 현재 프롬프트를 정량평가하는 방법은 [6개 도전 평가 계획](docs/ai-evaluation/six-category-quantitative-evaluation-plan.md)을 참고하세요.

## 프로젝트 구조

```text
src/moamu_ai/           FastAPI 앱, 요청 검증, 판정 서비스, 모델 제공자
tests/                  API·스키마·모델 어댑터·평가 테스트
data/evaluation/        평가용 JSONL 매니페스트
docs/ai-evaluation/     모델 선택, 프롬프트, 데이터셋, API 계약 기록
```
