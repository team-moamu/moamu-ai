# AI 사진 판정 평가 문서

모델, 프롬프트, 데이터셋 평가 절차와 API 계약을 Markdown으로 관리한다. 실제
벤치마크 실행 결과에는 사용 모델·프롬프트·데이터셋 조합과 측정 지표를 함께 기록해
재현할 수 있도록 한다.

## 문서 목록

- [모델 선정](model-selection.md): 후보 모델, 비교 방법, 비용 통제
- [프롬프트 실험](prompt-experiments.md): 버전별 프롬프트와 민감도 기록
- [데이터셋과 지표](dataset-and-metrics.md): 공개 데이터 출처, 라벨, 6개 도전 유형
- [벤치마크 실행 기록](benchmark-log.md): 실행 결과 양식과 현재 상태
- [6개 도전 긍정 이미지 스모크 평가](six-challenge-positive-smoke.md): 이미지 출처, 도전별 조건, Gemini 결과와 한계
- [AI 사진 판정 API 계약](api-contract.md): 내부 엔드포인트 계약과 오류 코드

## 벤치마크 실행

평가기는 기본적으로 모델을 호출하지 않는 미리보기 모드다. Gemini를 실제 호출하려면
`--execute`를 지정해야 한다. 키는 `.env`의 `GEMINI_TOKEN_API_KEY`에서 읽으며, 한 번
실행할 때 이미지 사례를 최대 6개로 제한한다. 자동 테스트는 가짜 provider를 사용하므로
Gemini API를 호출하지 않는다.

```bash
moamu-evaluate --manifest data/evaluation/manifest.jsonl --provider gemini --limit 6
moamu-evaluate --manifest data/evaluation/manifest.jsonl --provider gemini --limit 6 --execute
```

6개 도전 스모크 평가는 이미지 6장씩 세 번 실행하고 조건 문구를 확인하기 위해 이미지
3장을 추가로 재평가했다. 사용한 매니페스트와 결과는
[6개 도전 긍정 이미지 스모크 평가](six-challenge-positive-smoke.md)에 기록했다.

하나의 이미지 사례에서 모델 호출 한 번으로 조건 2~5개를 평가한다. 원시 실행 결과는
Git에서 제외되는 `data/evaluation/results/`에 저장한다. 이미지 파일은 저장소에 넣지 않고
`AI_IMAGE_ROOT` 설정 디렉터리 바깥에 보관한다. 매니페스트에는 이미지 출처 ID, 라벨,
라이선스를 기록한다.

실제 Gemini 호출에는 명시적으로 `--execute`를 넣어야 하므로 오프라인 테스트가 API 비용을
사용하지 않는다. 실행당 호출 수 제한도 그대로 적용된다.
