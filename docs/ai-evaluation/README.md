# AI 기능 평가 안내

연결된 Notion 페이지를 읽을 수 없어(404) 실험 기록을 Markdown 문서와 JSON 파일로 저장하고 있습니다. Notion 접근이 가능해지면 기록을 옮길 수 있도록 다시 확인합니다.

이 폴더의 기존 벤치마크 결과는 사진 인증 조건 판정 실험입니다. 2차 MVP의 자유목표 분석은 텍스트 입력과 다른 결과 기준을 사용하므로, 사진 판정 결과와 섞지 않고 [Notion 실험 기록 초안](notion-experiment-report.md)에서 별도 관리합니다. 자유목표 분석 모델·프롬프트 조합은 아직 정량 평가하지 않았습니다.

## 문서 목록

- [모델 선택](model-selection.md): 후보 모델, 비교 방법, 비용 관리 기준
- [사진 판정 프롬프트 실험 기록](prompt-experiments.md): 사진 판정 프롬프트 버전과 민감도 비교 기록
- [데이터셋과 지표](dataset-and-metrics.md): 공개 데이터 출처, 라벨, 6개 도전 유형
- [6개 도전 정량평가 계획](six-category-quantitative-evaluation-plan.md): 이미지 추가 수집, 라벨 검수, 표본 수, 지표, 프롬프트 조정 기준
- [6개 도전 v2/v4 파일럿 보고서](six-category-v2-pilot-20261102.md): Pexels 사진 30장 평가, Gemini 결과, 프롬프트 실험과 남은 검증 항목
- [Notion 실험 기록 표 초안](notion-experiment-report.md): 모델 테스트, 프롬프트 버전별 실험, 평가 데이터셋 표와 속성 정의
- [벤치마크 실행 기록](benchmark-log.md): 실행 결과를 기록하는 양식과 최신 진행 상태
- [6개 도전 긍정 사진 스모크 테스트](six-challenge-positive-smoke.md): 이미지 출처, 도전별 조건 2개, Gemini 결과와 한계
- [API 계약](api-contract.md): 내부 엔드포인트 요청·응답 형식과 오류 코드

## 사진 판정 평가 실행

평가 실행기는 기본적으로 실제 모델을 호출하지 않는 미리보기 모드로 동작합니다. Gemini를 실제 호출하려면 `--execute`를 지정해야 합니다. API 키는 `.env`의 `GEMINI_TOKEN_API_KEY`에서 읽으며, 한 번 실행할 때 최대 이미지 6장까지 처리합니다. 테스트는 가짜 모델을 사용하므로 Gemini API를 호출하지 않습니다.

```bash
# 실제 모델 호출 없이 매니페스트와 실행 설정 확인
moamu-evaluate --manifest data/evaluation/manifest.jsonl --provider gemini --limit 6 --prompt-version photo-verification-v2

# Gemini를 실제 호출해 최대 6개 사례 평가
moamu-evaluate --manifest data/evaluation/manifest.jsonl --provider gemini --limit 6 --prompt-version photo-verification-v2 --execute
```

6개 도전 긍정 사진 스모크 테스트는 6장씩 세 번 실행한 뒤, 조건 설명을 집중 재시험하기 위해 3장을 추가로 실행했습니다. 매니페스트와 결과는 [스모크 테스트 기록](six-challenge-positive-smoke.md)에 있습니다.

2026-11-02 프롬프트 비교 결과는 [6개 도전 파일럿 보고서](six-category-v2-pilot-20261102.md)에 기록했습니다. 같은 개발용 사진 30장으로 `photo-verification-v2`와 `photo-verification-v4`를 비교했습니다. 모델의 원본 응답 파일은 `data/evaluation/results/` 아래에서 Git에 포함하지 않고 관리합니다.

사진 판정 프롬프트는 `src/moamu_ai/prompt_versions/`에서 관리하고 `.env`의 `AI_PROMPT_VERSION`으로 선택합니다. 기본값은 `photo-verification-v4`입니다. 벤치마크 실행에서 `--prompt-version`을 지정하면 해당 버전을 사용하며, 결과 JSON에 선택한 버전과 해시가 기록됩니다.

자유목표 분석 프롬프트는 [`src/moamu_ai/goal_prompt_versions/`](../../src/moamu_ai/goal_prompt_versions/)에 따로 보존하고, `.env`의 `AI_GOAL_PROMPT_VERSION`으로 선택합니다. 현재 기본 버전은 `goal-verifiability-v1`입니다. 모델 공급자와 모델 ID 설정은 사진 판정 기능과 공유하며, 목표 분석 전용 모델 비교 결과는 아직 없습니다.

아래 `moamu-evaluate` 실행과 이 폴더의 이미지 데이터셋은 사진 판정용입니다. 자유목표 분석의 성능을 확인하려면 목표별 예상 상태와 응답 품질 기준을 검수한 텍스트 평가 세트를 먼저 만들고, 그 결과를 사진 평가와 분리해 기록해야 합니다.

사진 사례마다 조건 2~5개를 한 번의 모델 요청으로 평가합니다. 실행 결과는 Git에서 제외되는 `data/evaluation/results/`에 저장합니다. 이미지 파일은 저장소 밖의 `AI_IMAGE_ROOT` 경로에 두며, 매니페스트에는 출처 ID·라벨·라이선스를 기록합니다.

`--execute`를 지정하지 않으면 Gemini를 호출하지 않습니다. 실제 실행은 한 번에 최대 6장으로 제한되지만, 여러 번 실행할 때의 누적 비용을 자동으로 제한하지는 않습니다.
