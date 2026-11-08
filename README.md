# MOAMU AI 사진 인증 서버

백엔드가 전달한 S3 사진과 도전 인증 조건을 Gemini 또는 Ollama 비전 모델로 판정하는
내부 FastAPI 서비스다. API 계약과 모델·프롬프트·데이터셋 평가 문서는
[`docs/ai-evaluation/`](docs/ai-evaluation/)에 있다.

## 로컬 개발

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
test -f .env || cp .env.example .env
```

로컬 이미지 디렉터리를 사용하려면 `.env`에서 아래 값을 설정한다.

```dotenv
AI_IMAGE_SOURCE=local
AI_IMAGE_ROOT=./data/images
```

S3 사진을 시험하려면 `AI_IMAGE_SOURCE=s3`와 `S3_ACCESS_KEY_ID`,
`S3_SECRET_ACCESS_KEY`, `AWS_REGION`, `S3_BUCKET`을 설정한다. 비밀 키를 저장소에
커밋하지 않는다.

```bash
uvicorn moamu_ai.app:app --reload --host 127.0.0.1 --port 8000
```

API 문서는 `http://127.0.0.1:8000/docs`에서 확인할 수 있다. 엔드포인트는
`POST /internal/photo-verifications`이며 요청 형식은
[`api-contract.md`](docs/ai-evaluation/api-contract.md)를 참고한다.

## 오프라인 평가

라이선스가 확인된 로컬 이미지와 검수한 조건 라벨을 JSONL 매니페스트로 준비한다.
기본 실행은 API 모델을 호출하지 않는다.

```bash
moamu-evaluate --manifest data/evaluation/manifest.jsonl --provider gemini
```

실제 Gemini 호출은 `--execute`를 추가한다. 한 번에 실행하는 Gemini 이미지 호출은
최대 6회로 제한되어 있다. 저장된 실행 결과끼리 추가 호출 없이 비교할 수 있다.

```bash
moamu-compare-prompts results-v1.json results-v2.json
```

## 구성

- `src/moamu_ai/app.py`: FastAPI 라우트와 오류 응답
- `src/moamu_ai/service.py`: 이미지 조회, 모델 호출, 조건별 결과 대응
- `src/moamu_ai/image_sources.py`: S3 및 로컬 이미지 저장소
- `src/moamu_ai/prompt_versions/`: 프롬프트 버전별 정의
- `docs/ai-evaluation/`: 모델 선정과 평가 기록
