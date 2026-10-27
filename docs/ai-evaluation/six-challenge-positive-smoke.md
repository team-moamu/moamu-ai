# Six-challenge positive-image smoke evaluation

## Purpose and scope

This is a small, manually curated positive-only smoke set for the six challenge
types in the MOAMU photo-verification flow. It checks whether Gemini can detect
the visual evidence named in two required conditions per photo. It does not
measure overall model accuracy or the false-accept rate because it contains no
negative or ambiguous examples.

The 18 source photos were downloaded from Pexels on 2026-10-27, resized through
the Pexels image CDN to a maximum width of 640 pixels, and visually reviewed
before receiving `manual_review` positive labels. Pexels says its photos may be
used for free without attribution; the photo bytes stay in the ignored local
`data/images/` directory and are not committed. The manifests retain the source
page, creator, and license for each image. See the [Pexels license](https://www.pexels.com/license/).

## Required conditions

| Challenge | Condition 1 | Condition 2 |
|---|---|---|
| `STUDY_REVIEW` | A book, textbook, or other study material is visible. | A person's hand is writing or taking notes on paper. |
| `STAIRS_EXERCISE` | Stair steps are visible. | A person's foot is on a step or the person is visibly moving on the stairs. |
| `WATER_INTAKE` | A drinking cup or bottle is visible. | A person is visibly drinking from the cup or bottle. |
| `ALGORITHM_STUDY` | Source code or algorithm text is visible on a screen. | A person's hands are operating the keyboard. |
| `SUPPLEMENT_INTAKE` | A supplement or medicine container/package is visible. | Tablets or capsules are visible inside or outside the container. |
| `BADGE_CARRY` | An ID/name badge is visible. | The badge is held in a hand or worn with a lanyard/clip. |

These are image-level checks. A single still image cannot establish study duration,
exercise duration, that a drink is specifically water or was swallowed, that a
generic pill is a dietary supplement rather than medicine, or that a blank badge
belongs to the user. The code check only establishes visible code and typing; it
does not verify that an algorithm problem was solved.

## Curated photos and sources

Local relative paths are under
`data/images/six-challenge-pexels-20261027/<challenge>/`. SHA-256 hashes identify
the exact 640-pixel files used in this run.

| Challenge | Pexels ID | Creator | Source page | SHA-256 |
|---|---:|---|---|---|
| `STUDY_REVIEW` | `6237957` | Monstera Production | [Photo](https://www.pexels.com/photo/pensive-female-student-writing-notes-while-studying-in-light-room-6237957/) | `7f28ce3e6f10981fd89378f5ec6dfbcaecf1db81e5e52c0d66852872a286447f` |
| `STUDY_REVIEW` | `8199654` | Yan Krukau | [Photo](https://www.pexels.com/photo/a-person-taking-down-notes-8199654/) | `aa3d447a3316fbaef4c57633c65f61ac6503a3d724127cd8b637aff7c411f9f1` |
| `STUDY_REVIEW` | `7516544` | SHVETS production | [Photo](https://www.pexels.com/photo/woman-preparing-for-exam-in-library-7516544/) | `d93c800dc55e1c156d9b01b3f581e0ccc77cb89345f276328c86977d6d247660` |
| `STAIRS_EXERCISE` | `7880086` | MART PRODUCTION | [Photo](https://www.pexels.com/photo/woman-running-on-the-stairs-7880086/) | `189e1b698d373a94327990e906859059dab296e5f7c0559a007c542362e93b87` |
| `STAIRS_EXERCISE` | `4804029` | Ketut Subiyanto | [Photo](https://www.pexels.com/photo/person-climbing-the-concrete-stairs-4804029/) | `d1465d095a22964b0cd4118bebf99b5225bfee7ebf2276b32ce202294d60510e` |
| `STAIRS_EXERCISE` | `8554954` | Liliana Drew | [Photo](https://www.pexels.com/photo/a-man-walking-on-the-stairs-8554954/) | `582f339e1252d86d8f8d324ebbcc98c71ebe16cd3c624acae2e73baa06959da1` |
| `WATER_INTAKE` | `4853252` | Ketut Subiyanto | [Photo](https://www.pexels.com/photo/woman-drinking-from-bottle-of-water-4853252/) | `81d40ebfc7af34d622bd79f556868f7c502a0bb3e5a4ebad4eb8097c43d2e8e9` |
| `WATER_INTAKE` | `6766668` | KATRIN BOLOVTSOVA | [Photo](https://www.pexels.com/photo/woman-drinking-water-from-the-bottle-6766668/) | `6e635384fd221fb9c8a3db3d81bb94236eaf1aab975db9d832703e62f9327393` |
| `WATER_INTAKE` | `5088440` | cottonbro studio | [Photo](https://www.pexels.com/photo/a-man-drinking-water-from-a-glass-5088440/) | `ec6bfcc4358e72797d60c2609c83a87e484aece1e373927d72d39e8214022ee1` |
| `ALGORITHM_STUDY` | `5380591` | Tima Miroshnichenko | [Photo](https://www.pexels.com/photo/person-using-computer-5380591/) | `244efc4a237f57927a4944cde54c32a0f242af5186054cbac323607a66af4f3c` |
| `ALGORITHM_STUDY` | `36497969` | Jakub Zerdzicki | [Photo](https://www.pexels.com/photo/close-up-of-developer-typing-code-on-keyboard-36497969/) | `ae90e1f84ec02183d88216fa896409f7540af8bbec88dfcbce3e34ab8be9f3c4` |
| `ALGORITHM_STUDY` | `7988086` | Mikhail Nilov | [Photo](https://www.pexels.com/photo/a-person-doing-computer-programming-7988086/) | `36e66b30686a2048ddb2464d3b8be90d93926bea5ae747869139c116e85d790b` |
| `SUPPLEMENT_INTAKE` | `13013755` | Guto Macedo | [Photo](https://www.pexels.com/photo/man-holding-a-pill-and-a-bottle-in-his-hands-13013755/) | `9d6876d26d11b6d01661d5ca81243cf6cd97c064a4458b5a6faf3419edb21c9f` |
| `SUPPLEMENT_INTAKE` | `6798913` | Michelle Leman | [Photo](https://www.pexels.com/photo/woman-taking-pills-from-jar-on-hand-6798913/) | `142e183954c9f36cf391fcc0554c9159f21a2a19ef4519ccec25add0c638bf42` |
| `SUPPLEMENT_INTAKE` | `16051949` | Etatics Inc. | [Photo](https://www.pexels.com/photo/vial-with-pills-in-hand-16051949/) | `bdad94f2bbb0a571e4e89577a630beb6b34d5c290d5c3ac9c6120cf9fbb52034` |
| `BADGE_CARRY` | `7319161` | Angela Roma | [Photo](https://www.pexels.com/photo/cheerful-woman-showing-blank-name-tag-7319161/) | `54395ef75ad020ae8f6c9b16805591a9ae297d858e5ff222f9eb18431d69e4c8` |
| `BADGE_CARRY` | `26224976` | This And No Internet 25 | [Photo](https://www.pexels.com/photo/a-young-man-with-a-student-badge-standing-in-the-hallway-26224976/) | `4ae292c9312e39126e010a12e604c3abef96e9be19b3521968b1dfb0fee47811` |
| `BADGE_CARRY` | `9400290` | cottonbro studio | [Photo](https://www.pexels.com/photo/a-person-in-brown-coat-weaering-identification-badge-9400290/) | `976ea466916f474bffb5fc21a17b2b4916987400938a74e4fb84ddff8cd88d21` |

## Gemini runs

Model: `gemini-3.5-flash-lite`; stable prompt: `photo-verification-v1`;
dataset: development-only curated positives; 18 unique photos, two required
conditions each. Gemini's six-image-call cap was respected by running three
separate batches of six. A focused three-photo retest followed after correcting
one condition description. The API returned only the allowed condition status
values; no image bytes or API key were written to result files.

| Stage | Cases | Image calls | Condition predictions | MET | NOT_MET | UNCERTAIN | Estimated USD |
|---|---:|---:|---:|---:|---:|---:|---:|
| Initial wording (`v1` manifest) | 18 | 18 | 36 | 35 | 1 | 0 | `$0.0100306` |
| Supplement wording retest (`v2`, 3 supplement cases) | 3 | 3 | 6 | 6 | 0 | 0 | `$0.0017097` |
| Effective final positive set | 18 | 21 total calls | 36 | 36 | 0 | 0 | `$0.0117403` total |

The initial failure was `SUPPLEMENT_INTAKE / 16051949`: the image shows pills
inside a transparent vial, while the original condition required pills outside
the container. We changed that condition to include pills visible inside or
outside the container and reran all three supplement photos. The revised wording
returned `MET` for all six supplement-condition predictions. This is a useful
wording-sensitivity observation, not a general accuracy claim.

| Challenge | Initial version result | Final wording result |
|---|---|---|
| `STUDY_REVIEW` | 6/6 `MET` | 6/6 `MET` |
| `STAIRS_EXERCISE` | 6/6 `MET` | 6/6 `MET` |
| `WATER_INTAKE` | 6/6 `MET` | 6/6 `MET` |
| `ALGORITHM_STUDY` | 6/6 `MET` | 6/6 `MET` |
| `SUPPLEMENT_INTAKE` | 5/6 `MET`, 1/6 `NOT_MET` | 6/6 `MET` after wording revision |
| `BADGE_CARRY` | 6/6 `MET` | 6/6 `MET` |

Across the 21 calls, Gemini reported 27,751 input tokens and 1,366 output tokens.
At the current standard paid price of `$0.30` per million input tokens and
`$2.50` per million output tokens, the token-based estimate is `$0.0117403`.
This is not a billing receipt; Google AI Studio is the source for actual usage
and charges. The recorded aggregate p50/p95 latency was `1,819.25 / 2,869.04 ms`.

## Reproduction and interpretation

The current 18-case manifest is
[`data/evaluation/six-challenge-positive-20261027.jsonl`](../../data/evaluation/six-challenge-positive-20261027.jsonl).
The original condition wording is preserved in
[`data/evaluation/six-challenge-positive-v1-20261027.jsonl`](../../data/evaluation/six-challenge-positive-v1-20261027.jsonl).
Image files are ignored locally; if absent, download each Pexels photo at 640px
from its linked source page into the matching `image_path` before running. The
runner is dry-run by default, and Gemini is limited to six image calls per run.

The 18-case manifest is grouped in challenge order. To evaluate all photos in
three six-case calls, make three temporary manifests containing the first,
second, or third photo for each challenge, then run each with:

```bash
moamu-evaluate --manifest /tmp/six-challenge-batch-N.jsonl --provider gemini --limit 6 --execute
```

The exact raw run files stay under ignored `data/evaluation/results/`. Their run
IDs are `5a2e92a5-88f7-4e7d-8a67-327abed9a20e`,
`0de8984d-6189-41ea-afa9-4aab07d37834`,
`9b378510-4fd7-497f-8237-48d8f7b03e4e`, and the supplement retest
`664e9487-f5b0-4b36-bbd1-1a01912a4399`.

Because every photo was deliberately selected as a positive, false-accept rate
cannot be calculated. The final `36/36` condition pass rate only describes this
small curated set. A next benchmark needs hard negatives and ambiguous photos
for every challenge, especially images with medicine instead of supplements,
non-water drinks, code without active typing, and badges that are visible but
not carried or worn. Google's pricing page also states that free-tier API content
may be used to improve Google products, while paid-tier content is not; these
requests used public stock images, not user photos. Check the active billing/data
tier before evaluating private user images.
