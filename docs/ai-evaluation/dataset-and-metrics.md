# 평가 데이터셋과 지표

## 6개 도전 템플릿 범위

PRD에는 첫 출시 대상 도전 6개가 정의되어 있다. 아래 후보 시각 신호는 데이터셋과
도전을 연결하기 위한 제안이며, 제품/백엔드 팀이 최종 확정할 인증 조건 스냅샷을
대신하지 않는다.

| 도전 템플릿 코드 | 도전 | 공개 라벨로 찾을 수 있는 시작점 | 추가 라벨링이 필요한 항목 |
|---|---|---|---|
| `STUDY_REVIEW` | 공부·복습 | 책, 노트, 모니터, 노트북의 존재 | 의도한 공부 활동이 사진에 나타나는지 |
| `STAIRS_EXERCISE` | 계단 오르기 | 사람 및 계단/계단실 객체 | 사람과 계단의 관계 또는 행동. 객체 존재만으로는 부족 |
| `WATER_INTAKE` | 물 마시기 | 병, 컵, 유리잔의 존재 | 마시는 행동. 병만으로 음용을 증명할 수 없음 |
| `ALGORITHM_STUDY` | 알고리즘 공부 | 컴퓨터 또는 모니터의 존재 | 코드/내용과 의도한 공부 활동 |
| `SUPPLEMENT_INTAKE` | 영양제 복용 | 알약 또는 약 용기의 존재 | 영양제 식별/복용. 포장만으로 삼킴을 증명할 수 없음 |
| `BADGE_CARRY` | 명찰 휴대 | ID 카드, 목걸이줄, 명찰의 존재 | 명찰은 작거나 가려지는 경우가 많으므로 육안 검수가 필요 |

Open Images V7은 객체의 존재/부재와 일부 시각 관계를 확인하기 좋은 출발점이다.
사람이 검수한 이미지 단위 긍정·부정 라벨, 객체 상자, 관계/행동 주석이 포함된다.
**표시되지 않은 클래스는 부정 라벨이 아니라 미확인 상태다.** 객체 부재 사례에는
검증된 부정 라벨만 사용한다. 데이터셋은 주석 CC BY 4.0, 이미지 CC BY 2.0으로
표기하지만 이미지별 라이선스 확인도 권고한다. 이미지 ID, 원본 URL, 라이선스 근거,
라벨 근거를 매니페스트에 기록한다.

출처: [Open Images V7 정보, 라벨, 라이선스](https://storage.googleapis.com/openimages/web/factsfigures_v7.html).

### 6개 도전 선별 스모크 세트

현재 긍정 사례 작업 세트는 도전 템플릿마다 사람이 고른 Pexels 사진 3장으로
구성되어 있으며, [6개 도전 평가 기록](six-challenge-positive-smoke.md)의 정확한
2개 조건 스냅샷을 시험한다. 공개 라벨 데이터셋을 대체하는 세트가 아니라 작은
스모크 테스트다. 각 사례는 `manual_review` 라벨을 사용하고 기대 라벨은 모두 긍정이다.
성능을 주장하려면 독립 라벨링이 추가로 필요하다. Pexels 사진은 Git에서 제외되는
로컬 경로에 보관하며, 매니페스트에는 원본 페이지, 제작자, Pexels 라이선스를 기록한다.
Pexels 라이선스는 출처 표시 없이 무료 사용을 허용하지만, 원본 사진은 이 저장소에
커밋하지 않는다.

## 라벨링 절차

- `human_verified_positive`는 라벨이 나타내는 구체적 관찰 조건의 기대값 `MET`에 대응한다.
- `human_verified_negative`는 해당 클래스에 대한 명시적 검증 부정 라벨이 있을 때만 기대값 `NOT_MET`에 대응한다.
- `manual_review`는 검수자가 MOAMU 조건에 맞춰 직접 부여한 라벨이다. 실제로 모호하거나 가려진 경우 기대값을 `UNCERTAIN`으로 둔다. 그 외에는 근거를 기록해 `MET` 또는 `NOT_MET`으로 라벨링한다. 현재 Pexels 스모크 라벨은 검수자 1명의 1차 육안 검토 결과이므로, 정답 기준으로 쓰기 전에 프로젝트 차원의 독립 검수가 필요하다.
- 주석 누락, 신뢰도가 낮은 자동 생성 라벨, 라이선스가 불확실한 이미지는 점수 산정에서 제외한다.
- 프롬프트를 조정하기 전에 이미지 ID 기준으로 `dev`와 `held_out`을 나눈다. held-out 결과를 보고 프롬프트를 튜닝하지 않는다.

## JSONL 매니페스트 필드

비어 있지 않은 각 줄은 이미지 요청 하나를 나타낸다. API 호출 수를 줄이기 위해 한
요청에 조건 2~5개를 평가할 수 있다. `AI_IMAGE_ROOT` 기준 상대 경로를 저장한다.

```json
{
  "case_id": "open-images-v7-<image-id>-water",
  "goal_template_code": "WATER_INTAKE",
  "dataset_name": "Open Images V7",
  "dataset_version": "v7",
  "dataset_split": "validation",
  "dataset_image_id": "<image-id>",
  "image_license": "CC BY 2.0; per-image license verified",
  "image_source_url": "https://...",
  "split": "dev",
  "image_path": "open-images-v7/<image-id>.jpg",
  "conditions": [
    {"challenge_condition_id": 101, "code": "C1", "condition_type": "OBJECT_PRESENT", "description": "물병이 사진에 보여야 한다", "required": true, "sort_order": 1},
    {"challenge_condition_id": 102, "code": "C2", "condition_type": "ACTIVITY_IN_PROGRESS", "description": "사람이 물을 마시는 모습이 사진에 보여야 한다", "required": true, "sort_order": 2}
  ],
  "expected_results": [
    {"challenge_condition_id": 101, "status": "MET", "label_basis": "human_verified_positive"},
    {"challenge_condition_id": 102, "status": "UNCERTAIN", "label_basis": "manual_review"}
  ]
}
```

`dataset_split`은 원본 데이터셋의 분할을 기록한다. `split`은 MOAMU 평가용 `dev` 또는
`held_out` 분할을 나타낸다. 문서 예시에는 합성 ID만 사용한다. 실제 사례를 평가하기
전에 공개 데이터셋의 정확한 이미지 ID와 라이선스를 확인한다.

## 지표

- 전체 및 조건 코드별 3-way 혼동 행렬과 macro-F1.
- 오승인율: 정답 `NOT_MET` 사례 중 `MET`으로 예측한 수의 비율.
- 오거절율: 정답 `MET` 사례 중 `NOT_MET`으로 예측한 수의 비율.
- 실행에 `NOT_MET` 라벨이 없으면 오승인율은 정의되지 않으므로 `null`로 기록한다. `MET` 라벨이 없으면 오거절율을 `null`로 기록한다.
- coverage: 전체 예측 중 `UNCERTAIN`이 아닌 예측의 비율.
- selective accuracy: `UNCERTAIN`을 제외한 예측 중 정답 비율.
- `UNCERTAIN` 건수와 비율을 별도로 보고한다. 공개 데이터의 이진 라벨만으로는 `UNCERTAIN` 응답이 옳은지 판단할 수 없으며, 모호 사례에 대한 수동 라벨링이 필요하다.
- 요청 지연 시간, 모델이 보고한 입력/출력 토큰 수, Ollama의 CPU/RAM 사용량을 기록한다. 조건별 정성 오류 유형도 포함한다.

벤치마크 실행기는 비용 통제를 위해 기본적으로 dry-run으로 동작한다. Gemini를
실행하려면 `--execute`가 필요하며 한 번에 이미지 사례를 최대 6개까지 처리한다.
CPU 지연 시간이 허용된다면 더 큰 실험에는 로컬 Ollama 제공자를 사용한다.
