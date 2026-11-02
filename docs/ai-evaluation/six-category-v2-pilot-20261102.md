# 6개 도전 사진 판정 파일럿: v2와 v4 비교

| 항목 | 값 |
|---|---|
| 실행일 | 2026-11-02 |
| 모델 | Gemini API / `gemini-3.5-flash-lite` |
| 런타임 | Python 3.13.5, `google-genai` 1.75.0 |
| 데이터 | Pexels 사진 30장: 기존 긍정 18장 + 신규 혼합 사례 12장 |
| 조건별 예측 | 프롬프트 버전마다 60개 |
| 라벨 | 조건별 `MET` / `NOT_MET`, 단일 검수자의 수동 검토 |
| 세트 | 전체 `dev`; held-out 없음 |

## 결과 요약

각 사진은 조건 두 개를 평가했다. 모든 템플릿 조건은 `required`였으며, 이 문서의 지표는 **조건 단위**다. 백엔드의 최종 사진 승인 집계 지표로 해석하지 않는다.

| 프롬프트 | 정답 일치 | 정확도 | 오승인 | 오승인율 | 오거절 | `UNCERTAIN` | 토큰 기반 비용 추정 |
|---|---:|---:|---:|---:|---:|---:|---:|
| `photo-verification-v2` | 57/60 | 95.0% | 1/12 | 8.3% | 0/48 | 2/60 | `$0.0164900` |
| `photo-verification-v4` | 58/60 | 96.7% | 0/12 | 0% | 1/48 | 1/60 | `$0.0172850` |

v4는 v2와 비교해 예측 두 개가 바뀌었다(2/60, 3.3%). 구미 사진을 정제·캡슐로 오인한 오승인은 `MET`에서 `NOT_MET`으로 바뀌었다. 공부 긍정 사진 한 장의 필기 조건은 `UNCERTAIN`에서 `NOT_MET`으로 바뀌어 오거절이 됐다. 조건별 전체 정확도는 95.0%에서 96.7%로 올랐지만, 여섯 카테고리 각각의 부정 조건 표본은 두 개뿐이다. **v4는 다음 검증 후보로 두며, PRD 품질 기준을 통과했다고 판단하지 않는다.**

| 도전 | 조건 예측 수 | v2 일치 | v2 오류 | v4 일치 | v4 오류 |
|---|---:|---:|---|---:|---|
| 공부 | 10 | 9/10 | 1 `UNCERTAIN` | 9/10 | 1 오거절 |
| 계단 운동 | 10 | 10/10 | 없음 | 10/10 | 없음 |
| 물 마시기 | 10 | 10/10 | 없음 | 10/10 | 없음 |
| 알고리즘 학습 | 10 | 10/10 | 없음 | 10/10 | 없음 |
| 영양제 | 10 | 8/10 | 오승인 1, `UNCERTAIN` 1 | 9/10 | `UNCERTAIN` 1 |
| 명찰 | 10 | 10/10 | 없음 | 10/10 | 없음 |

### 판정 원인

- `SUPPLEMENT_INTAKE / 7468582 / condition 642`: 병 안의 구미 젤리를 정제·캡슐 조건으로 오인했다. v2의 유일한 오승인이다. v4는 사진에서 확인되는 형태를 기준으로 `NOT_MET`을 반환했다.
- `SUPPLEMENT_INTAKE / 8670519 / condition 642`: 불투명한 약병 안에 정제·캡슐이 보이지 않는다. v2와 v4 모두 확정하지 않고 `UNCERTAIN`을 반환했다.
- `STUDY_REVIEW / 7516544 / condition 602`: Pexels 설명은 필기 사진으로 소개하지만, 원본을 확대해도 펜 끝과 종이의 접촉이 선명하지 않다. 기존 데이터의 단일 검수 라벨은 `MET`이다. v2의 `UNCERTAIN`과 v4의 `NOT_MET`을 성능 오류로 단정하기 전에 독립 검수자가 라벨을 다시 정해야 한다.

## 프롬프트 조정 기록

1. v2 기준선에서 구미를 캡슐로 오인한 오승인을 발견했다.
2. v3에 “구체적으로 이름 붙인 물체·행동·속성이 보여야 하고, 비슷하거나 관련된 항목으로 대체하지 않는다”는 지침을 추가했다. 보충 2장 평가에서 불투명 약병은 `UNCERTAIN`에서 `NOT_MET`으로 바뀌었지만 구미 오승인은 남았다. v3은 채택하지 않았다.
3. v4에 형태 조건 예시를 하나 더했다: “구미 사탕은 정제나 캡슐이 아니다.” v4를 동일한 30장으로 재평가했다. 구미 오승인은 사라졌고 다른 예측 한 개가 바뀌었다.

v4가 한 번의 소규모 개발 세트에서 오승인을 줄였지만, 이 결과만으로 튜닝 효과를 일반화하지 않는다. 보류·오거절 trade-off를 확인하려면 공부 행동의 모호 사례와 영양제의 다양한 형태를 보강하고, 두 명이 모델 결과를 보지 않은 채 조건별 라벨을 붙여야 한다.

## 신규 이미지와 라벨

사진 원본은 Pexels에서 받았고, 1280px 폭 파일을 `AI_IMAGE_ROOT` 아래에 두었다. Pexels는 사진 무료 사용과 출처 표시 불필요를 안내하지만, 변형하지 않은 사진의 재판매와 다른 스톡·배경화면 플랫폼 재배포를 금지한다. 원본 파일은 Git에 넣지 않고 로컬 `data/images/six-category-pilot-20261102/` 아래에만 보관한다. [Pexels 라이선스](https://www.pexels.com/license/)와 각 사진 페이지를 확인한다.

새 12장은 모두 조건별 한 번의 수동 검수를 거쳤다. `MET/NOT_MET`은 조건 설명 그대로의 시각 증거를 기준으로 붙였다. 각 사례는 조건 하나가 보이고 다른 하나는 충족하지 않는 형태다.

| 도전 | 이미지 / 제작자 | 수동 라벨 (조건 순서대로) | SHA-256 |
|---|---|---|---|
| 공부 | [9871139 · Ron Lach](https://www.pexels.com/photo/open-books-lying-on-desk-9871139/) | `MET`, `NOT_MET` | `4c29cd44b7070672257a1ba986d1486979583b0c9f79d4dd2c24c1df2fff224a` |
| 계단 운동 | [9198397 · yu zhou](https://www.pexels.com/photo/empty-staircase-9198397/) | `MET`, `NOT_MET` | `3d969511d57737b2cec46f4872f1c174356b1d6dac6106f86f53e40018283e2f` |
| 물 마시기 | [11031202 · MOISES RIBEIRO](https://www.pexels.com/photo/a-black-and-stainless-bottle-11031202/) | `MET`, `NOT_MET` | `ff663cfa103478679dc812a98df02e78726d3bce478fc1bfebd1eb6d796320e8` |
| 알고리즘 학습 | [6279113 · Artem Podrez](https://www.pexels.com/photo/photo-of-a-person-typing-on-a-laptop-6279113/) | `NOT_MET`, `MET` | `fd890e9faba188dbd42ed7b279e5e19e71942ad200875b80987b6de1e6f49e09` |
| 영양제 | [8670519 · Mikhail Nilov](https://www.pexels.com/photo/woman-holding-a-medicine-container-8670519/) | `MET`, `NOT_MET` | `cd675d851af0f9df971ca4d8d10e203994b3e05716932d394d00d63157dff0c3` |
| 명찰 | [7648025 · RDNE Stock project](https://www.pexels.com/photo/id-s-on-the-table-7648025/) | `MET`, `NOT_MET` | `d0e1d03c01f63f2eb79e9ad08e5b1f3b1653a74e4367da9621676650b2e9dfec` |
| 공부 | [13105769 · Elifnur Gökmenoğlu](https://www.pexels.com/photo/book-and-smartphone-on-desk-13105769/) | `MET`, `NOT_MET` | `feb6387df09a9f6c7aee3cdda6a0b277d171d0a53645bf04afadcfe96d8cb400` |
| 계단 운동 | [11960800 · Don Redman](https://www.pexels.com/photo/an-empty-concrete-stairs-11960800/) | `MET`, `NOT_MET` | `b9d88d0efa0747c345124e10dee71cb26e100913252ae06f3c3556fa7c391859` |
| 물 마시기 | [7537474 · Gamze Özdemir](https://www.pexels.com/photo/a-person-holding-a-drinking-bottle-7537474/) | `MET`, `NOT_MET` | `27fc2c03dfacad6dd7cf61c8c112315b30de9715201ced5b366ae6e2adf07f84` |
| 알고리즘 학습 | [7864378 · VAZHNIK](https://www.pexels.com/photo/a-person-typing-on-a-laptop-7864378/) | `NOT_MET`, `MET` | `225383846d96823371896ffcbf744a34a2eb56653fbde48a92dbfdd0847c0d13` |
| 영양제 | [7468582 · Jellybee](https://www.pexels.com/photo/close-up-photo-of-a-bottle-with-vitamins-7468582/) | `MET`, `NOT_MET` | `f2cbbf755ac4422d12423cfe1bffb7e98b7faa4a0d28f4066686de155b2a8d4d` |
| 명찰 | [8761738 · Pavel Danilyuk](https://www.pexels.com/photo/paper-printout-badge-and-a-microphone-on-gray-surface-8761738/) | `MET`, `NOT_MET` | `3198577d5de1064167162db778e82044bb27ec0ababc768e15315b2c13e597c4` |

원본 18장과 새 12장을 합친 재현용 매니페스트는
[`six-challenge-v2-pilot-20261102.jsonl`](../../data/evaluation/six-challenge-v2-pilot-20261102.jsonl)이다. 이전 18장 양성 사진 상세 출처와 해시는 [기존 긍정 스모크 문서](six-challenge-positive-smoke.md)에 있다.

## 실행·비용

Gemini는 이미지마다 한 번 호출했다. v2와 v4는 각각 30장씩, v3 보충 확인은 2장으로 총 62회 호출했다. 토큰 기록에 Google의 Standard 유료 단가(입력 `$0.30`/1M, 출력 `$2.50`/1M)를 적용한 합계 추정은 `$0.0349255`다. 이는 실제 청구 금액이 아니다. 실행 시각의 요금 정보는 [Google Gemini API 가격표](https://ai.google.dev/gemini-api/docs/pricing)를 확인했다.

| 실행 | 이미지 호출 | 입력/출력 토큰 | 추정 비용 | p50 / p95 |
|---|---:|---:|---:|---:|
| v2 기준선 | 30 | 38,000 / 2,036 | `$0.0164900` | 2,017 / 3,154 ms |
| v3 보충 확인 | 2 | 2,685 / 138 | `$0.0011505` | 2,805 / 3,573 ms |
| v4 동일 세트 재검사 | 30 | 40,400 / 2,066 | `$0.0172850` | 1,573 / 2,341 ms |

실행기의 1회 호출 상한(6장)을 지켜 각 30장 세트를 다섯 배치로 실행했다. 결과 JSON은 `data/evaluation/results/` 아래 Git 무시 경로에 저장했다. 파일별 결과와 v2/v4 상태 비교 JSON도 로컬에서 확인할 수 있다.

## 해석과 다음 단계

- Gemini 판정은 조건 설명의 시각적 증거에만 적용했다. 사진이 실제 물 섭취, 장시간 운동, 공부 의도, 영양제 복용을 입증하지는 않는다.
- 특히 현재 `SUPPLEMENT_INTAKE` 조건은 포장과 정제·캡슐의 가시성을 확인하며 실제 섭취를 확인하지 않는다. 실제 “복용” 인증이 목적이면 백엔드가 조건 정의를 바꿔야 한다. 이미지 한 장으로 삼킴 여부를 확정한다고 프롬프트가 주장해서는 안 된다.
- 매니페스트의 `challenge_condition_id`와 `code`는 기존 AI 내부 스모크 세트의 예시 값이다. 새 테스트에서 `condition_type`은 현재 API가 허용하는 값으로 맞췄지만, 이 매니페스트는 백엔드의 실제 여섯 템플릿 스냅샷이 아니다. 실연동 검증 전에 백엔드 담당자가 실제 ID·코드·설명·필수 여부를 제공해야 한다.
- 부정 조건이 카테고리마다 두 개뿐이라 오승인율 0%는 성공 기준을 입증하지 못한다. 계획서 기준대로 카테고리별 충분한 독립 음성 사례와 별도 held-out 세트를 모으고, 최소 두 명의 검수자가 모델 결과를 가린 채 라벨을 확정한다.
- 프롬프트는 v4를 후보로 보존하고, 현재는 추가 문구를 더 튜닝하지 않는다. 다음 변경 전 라벨 문제(특히 `7516544`)를 정리하고, 더 다양한 구미·정제·불투명 용기·일반 약품 사례를 모은다.
