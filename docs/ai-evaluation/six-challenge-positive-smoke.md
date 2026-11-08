# 6개 도전 긍정 사진 스모크 평가

## 목적과 범위

이 문서는 MOAMU 사진 판정 흐름에서 사용하는 6개 도전 유형을 대상으로 직접 선별한
작은 긍정 전용 스모크 세트를 기록한다. 사진마다 필수 조건 2개에 명시된 시각 증거를
Gemini가 찾는지 확인한다. 부정 또는 모호 사례가 없으므로 전체 모델 정확도나 오승인율은
측정하지 않는다.

원본 사진 18장은 2026-10-27에 Pexels에서 내려받았다. Pexels 이미지 CDN을 이용해
최대 너비 640픽셀로 조정하고 육안 검토한 뒤 `manual_review` 긍정 라벨을 붙였다.
Pexels는 사진을 출처 표시 없이 무료로 사용할 수 있다고 안내한다. 이미지 바이트는
Git에서 제외되는 로컬 `data/images/` 디렉터리에만 두고 저장소에 커밋하지 않았다.
매니페스트에는 이미지별 원본 페이지, 제작자, 라이선스를 기록했다.
[Pexels 라이선스](https://www.pexels.com/license/)를 참고한다.

## 인증 필수 조건

| 도전 | 조건 1 | 조건 2 |
|---|---|---|
| `STUDY_REVIEW` | 책, 교재 또는 기타 학습 자료가 보여야 한다. | 사람이 손으로 종이에 글을 쓰거나 필기하는 모습이 보여야 한다. |
| `STAIRS_EXERCISE` | 계단이 보여야 한다. | 사람의 발이 계단을 밟고 있거나 계단을 이동하는 모습이 보여야 한다. |
| `WATER_INTAKE` | 물컵 또는 물병이 보여야 한다. | 컵이나 병으로 물을 마시는 모습이 보여야 한다. |
| `ALGORITHM_STUDY` | 화면에 소스 코드 또는 알고리즘 텍스트가 보여야 한다. | 사람이 키보드를 조작하는 손이 보여야 한다. |
| `SUPPLEMENT_INTAKE` | 영양제 또는 약의 용기/포장이 보여야 한다. | 용기 안이나 밖에 정제 또는 캡슐이 보여야 한다. |
| `BADGE_CARRY` | ID 카드 또는 이름표가 보여야 한다. | 손으로 들고 있거나 목걸이줄/클립으로 착용한 모습이어야 한다. |

이 조건은 이미지에서 확인할 수 있는 항목만 다룬다. 정지 사진 한 장으로는 공부나
운동의 지속 시간, 음료가 실제로 물인지 또는 삼켰는지, 일반 알약이 영양제인지 약인지,
비어 있는 명찰이 사용자 소유인지 확인할 수 없다. 알고리즘 조건은 코드와 타이핑이
보이는지만 확인하며 알고리즘 문제를 풀었는지는 검증하지 않는다.

## 선별 사진과 출처

로컬 상대 경로는 `data/images/six-challenge-pexels-20261027/<challenge>/` 아래에 있다.
SHA-256 해시는 이번 실행에서 사용한 640픽셀 이미지 파일을 식별한다.

| 도전 | Pexels ID | 제작자 | 원본 페이지 | SHA-256 |
|---|---:|---|---|---|
| `STUDY_REVIEW` | `6237957` | Monstera Production | [사진](https://www.pexels.com/photo/pensive-female-student-writing-notes-while-studying-in-light-room-6237957/) | `7f28ce3e6f10981fd89378f5ec6dfbcaecf1db81e5e52c0d66852872a286447f` |
| `STUDY_REVIEW` | `8199654` | Yan Krukau | [사진](https://www.pexels.com/photo/a-person-taking-down-notes-8199654/) | `aa3d447a3316fbaef4c57633c65f61ac6503a3d724127cd8b637aff7c411f9f1` |
| `STUDY_REVIEW` | `7516544` | SHVETS production | [사진](https://www.pexels.com/photo/woman-preparing-for-exam-in-library-7516544/) | `d93c800dc55e1c156d9b01b3f581e0ccc77cb89345f276328c86977d6d247660` |
| `STAIRS_EXERCISE` | `7880086` | MART PRODUCTION | [사진](https://www.pexels.com/photo/woman-running-on-the-stairs-7880086/) | `189e1b698d373a94327990e906859059dab296e5f7c0559a007c542362e93b87` |
| `STAIRS_EXERCISE` | `4804029` | Ketut Subiyanto | [사진](https://www.pexels.com/photo/person-climbing-the-concrete-stairs-4804029/) | `d1465d095a22964b0cd4118bebf99b5225bfee7ebf2276b32ce202294d60510e` |
| `STAIRS_EXERCISE` | `8554954` | Liliana Drew | [사진](https://www.pexels.com/photo/a-man-walking-on-the-stairs-8554954/) | `582f339e1252d86d8f8d324ebbcc98c71ebe16cd3c624acae2e73baa06959da1` |
| `WATER_INTAKE` | `4853252` | Ketut Subiyanto | [사진](https://www.pexels.com/photo/woman-drinking-from-bottle-of-water-4853252/) | `81d40ebfc7af34d622bd79f556868f7c502a0bb3e5a4ebad4eb8097c43d2e8e9` |
| `WATER_INTAKE` | `6766668` | KATRIN BOLOVTSOVA | [사진](https://www.pexels.com/photo/woman-drinking-water-from-the-bottle-6766668/) | `6e635384fd221fb9c8a3db3d81bb94236eaf1aab975db9d832703e62f9327393` |
| `WATER_INTAKE` | `5088440` | cottonbro studio | [사진](https://www.pexels.com/photo/a-man-drinking-water-from-a-glass-5088440/) | `ec6bfcc4358e72797d60c2609c83a87e484aece1e373927d72d39e8214022ee1` |
| `ALGORITHM_STUDY` | `5380591` | Tima Miroshnichenko | [사진](https://www.pexels.com/photo/person-using-computer-5380591/) | `244efc4a237f57927a4944cde54c32a0f242af5186054cbac323607a66af4f3c` |
| `ALGORITHM_STUDY` | `36497969` | Jakub Zerdzicki | [사진](https://www.pexels.com/photo/close-up-of-developer-typing-code-on-keyboard-36497969/) | `ae90e1f84ec02183d88216fa896409f7540af8bbec88dfcbce3e34ab8be9f3c4` |
| `ALGORITHM_STUDY` | `7988086` | Mikhail Nilov | [사진](https://www.pexels.com/photo/a-person-doing-computer-programming-7988086/) | `36e66b30686a2048ddb2464d3b8be90d93926bea5ae747869139c116e85d790b` |
| `SUPPLEMENT_INTAKE` | `13013755` | Guto Macedo | [사진](https://www.pexels.com/photo/man-holding-a-pill-and-a-bottle-in-his-hands-13013755/) | `9d6876d26d11b6d01661d5ca81243cf6cd97c064a4458b5a6faf3419edb21c9f` |
| `SUPPLEMENT_INTAKE` | `6798913` | Michelle Leman | [사진](https://www.pexels.com/photo/woman-taking-pills-from-jar-on-hand-6798913/) | `142e183954c9f36cf391fcc0554c9159f21a2a19ef4519ccec25add0c638bf42` |
| `SUPPLEMENT_INTAKE` | `16051949` | Etatics Inc. | [사진](https://www.pexels.com/photo/vial-with-pills-in-hand-16051949/) | `bdad94f2bbb0a571e4e89577a630beb6b34d5c290d5c3ac9c6120cf9fbb52034` |
| `BADGE_CARRY` | `7319161` | Angela Roma | [사진](https://www.pexels.com/photo/cheerful-woman-showing-blank-name-tag-7319161/) | `54395ef75ad020ae8f6c9b16805591a9ae297d858e5ff222f9eb18431d69e4c8` |
| `BADGE_CARRY` | `26224976` | This And No Internet 25 | [사진](https://www.pexels.com/photo/a-young-man-with-a-student-badge-standing-in-the-hallway-26224976/) | `4ae292c9312e39126e010a12e604c3abef96e9be19b3521968b1dfb0fee47811` |
| `BADGE_CARRY` | `9400290` | cottonbro studio | [사진](https://www.pexels.com/photo/a-person-in-brown-coat-weaering-identification-badge-9400290/) | `976ea466916f474bffb5fc21a17b2b4916987400938a74e4fb84ddff8cd88d21` |

## Gemini 실행

모델은 `gemini-3.5-flash-lite`, 고정 프롬프트는 `photo-verification-v1`이다. 데이터는
개발 전용으로 선별한 긍정 사례 18장이고 사진마다 필수 조건 2개를 평가했다. Gemini의
이미지 호출 6회 제한에 맞춰 6장씩 세 번 나누어 실행했다. 조건 설명 하나를 수정한 뒤
영양제 사진 3장을 추가로 재시험했다. API는 허용된 조건 상태값만 반환했으며, 결과
파일에는 이미지 바이트나 API 키를 저장하지 않았다.

| 단계 | 사례 | 이미지 호출 | 조건별 예측 | MET | NOT_MET | UNCERTAIN | 예상 비용 (USD) |
|---|---:|---:|---:|---:|---:|---:|---:|
| 최초 문구 (`v1` 매니페스트) | 18 | 18 | 36 | 35 | 1 | 0 | `$0.0100306` |
| 영양제 문구 재시험 (`v2`, 영양제 사례 3개) | 3 | 3 | 6 | 6 | 0 | 0 | `$0.0017097` |
| 최종 반영 긍정 세트 | 18 | 총 21회 | 36 | 36 | 0 | 0 | 총 `$0.0117403` |

최초 실패는 `SUPPLEMENT_INTAKE / 16051949`였다. 사진에는 투명한 병 안에 알약이
보이지만 최초 조건은 병 밖의 알약을 요구했다. 병 안팎의 알약을 모두 포함하도록
조건 설명을 바꾸고 영양제 사진 3장을 다시 평가했다. 수정된 설명에서는 영양제 조건
예측 6개가 모두 `MET`이었다. 이는 문구 민감도 관찰 사례이며 일반적인 정확도 주장은
아니다.

| 도전 | 최초 버전 결과 | 문구 수정 후 결과 |
|---|---|---|
| `STUDY_REVIEW` | `MET` 6/6 | `MET` 6/6 |
| `STAIRS_EXERCISE` | `MET` 6/6 | `MET` 6/6 |
| `WATER_INTAKE` | `MET` 6/6 | `MET` 6/6 |
| `ALGORITHM_STUDY` | `MET` 6/6 | `MET` 6/6 |
| `SUPPLEMENT_INTAKE` | `MET` 5/6, `NOT_MET` 1/6 | 문구 수정 후 `MET` 6/6 |
| `BADGE_CARRY` | `MET` 6/6 | `MET` 6/6 |

21회 호출에서 Gemini는 입력 토큰 27,751개, 출력 토큰 1,366개를 보고했다. 유료 표준
가격(입력 토큰 100만 개당 `$0.30`, 출력 토큰 100만 개당 `$2.50`) 기준 토큰 비용
추정치는 `$0.0117403`이다. 실제 청구 내역이 아니며 실제 사용량과 비용은 Google AI
Studio에서 확인해야 한다. 기록된 전체 p50/p95 지연 시간은 `1,819.25 / 2,869.04 ms`다.

## 재현 방법과 해석

현재 18개 사례 매니페스트는
[`data/evaluation/six-challenge-positive-20261027.jsonl`](../../data/evaluation/six-challenge-positive-20261027.jsonl)에
있다. 최초 조건 문구는
[`data/evaluation/six-challenge-positive-v1-20261027.jsonl`](../../data/evaluation/six-challenge-positive-v1-20261027.jsonl)에
보존했다. 이미지 파일은 로컬에서 Git 제외 처리되어 있다. 파일이 없으면 각 Pexels
원본 페이지에서 640px 사진을 내려받아 해당 `image_path`에 저장한다. 실행기는 기본
dry-run이며 Gemini 호출은 한 번에 최대 6회다.

18개 사례 매니페스트는 도전 순서로 정렬되어 있다. 모든 사진을 6개씩 세 번 호출해
평가하려면 도전별 첫 번째, 두 번째, 세 번째 사진을 모은 임시 매니페스트를 만든 뒤
각각 아래처럼 실행한다.

```bash
moamu-evaluate --manifest /tmp/six-challenge-batch-N.jsonl --provider gemini --limit 6 --execute
```

정확한 원본 결과 파일은 Git에서 제외되는 `data/evaluation/results/`에 보관한다. 실행
ID는 `5a2e92a5-88f7-4e7d-8a67-327abed9a20e`,
`0de8984d-6189-41ea-afa9-4aab07d37834`,
`9b378510-4fd7-497f-8237-48d8f7b03e4e`, 영양제 재시험은
`664e9487-f5b0-4b36-bbd1-1a01912a4399`다.

모든 사진을 긍정 사례로 선별했으므로 오승인율은 계산할 수 없다. 최종 조건 통과
`36/36`은 이 작은 선별 세트에만 해당한다. 다음 벤치마크에는 각 도전의 어려운 부정·모호
사례가 필요하다. 특히 영양제가 아닌 일반 약, 물이 아닌 음료, 타이핑 없이 코드만 보이는
화면, 눈에 보이지만 휴대하거나 착용하지 않은 명찰 사례를 추가해야 한다. Google 가격
안내에 따르면 무료 등급의 API 입력은 Google 제품 개선에 사용될 수 있지만 유료 등급의
입력은 그렇지 않다. 이 실행에서는 사용자 사진이 아닌 공개 스톡 사진을 사용했다.
비공개 사용자 사진을 평가하기 전에 현재 결제·데이터 처리 등급을 확인한다.
