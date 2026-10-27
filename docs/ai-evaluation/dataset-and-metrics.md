# Evaluation dataset and metrics

## Six GoalTemplate coverage

The PRD lists six first-release goals. These candidate visual signals are a
dataset-mapping proposal; they do not replace the final frozen condition snapshots
selected by the product/backend team.

| GoalTemplate code | Goal | Public-label starting point | Extra labeling needed |
|---|---|---|---|
| `STUDY_REVIEW` | Review/study | Book, notebook, monitor, or laptop presence | Whether the image shows the intended study activity |
| `STAIRS_EXERCISE` | Climb stairs | Person and stair/staircase objects | Person-on-stairs relation or action; object presence alone is insufficient |
| `WATER_INTAKE` | Drink water | Bottle, cup, or glass presence | Drinking action; a bottle alone does not prove consumption |
| `ALGORITHM_STUDY` | Study algorithms | Computer or monitor presence | Code/content and the intended study activity |
| `SUPPLEMENT_INTAKE` | Take supplements | Pill or medicine container presence | Supplement identity/intake; package presence does not prove swallowing |
| `BADGE_CARRY` | Carry a name badge | ID card, lanyard, or badge presence | Badge is often small/occluded; manually verify visibility |

Open Images V7 is a useful starting point for object presence/absence and some
visual relations. It contains human-verified image-level positive and negative
labels, object boxes, and relationship/action annotations. **An unmarked class is
unknown, not a negative label.** Use only explicit verified negatives for absence
cases. The dataset says annotations are CC BY 4.0 and images are listed as CC BY
2.0, while also advising users to verify each image's license. Keep the image ID,
source URL, license evidence, and label basis in the manifest.

Source: [Open Images V7 facts, labels, and license](https://storage.googleapis.com/openimages/web/factsfigures_v7.html).

### Curated six-challenge smoke set

The current positive-only working set uses three manually selected Pexels photos
per goal template to exercise the exact two-condition snapshots in the
[`six-challenge evaluation record`](six-challenge-positive-smoke.md). It is a
small smoke set, not a replacement for an open labeled dataset: each case uses
`manual_review`, has only positive expected labels, and needs independent
annotation before it can support a performance claim. Pexels images are kept in
ignored local paths; manifests record source pages, creators, and the Pexels
license. The Pexels license permits free use without attribution, but the source
photos are not committed to this repository.

## Labeling protocol

- `human_verified_positive` maps to expected `MET` for the specific observable
  condition represented by that label.
- `human_verified_negative` maps to expected `NOT_MET` only when that exact class
  has an explicit verified negative label.
- `manual_review` is for a reviewer-assigned MOAMU-specific condition label. Use
  expected `UNCERTAIN` for genuinely ambiguous/occluded cases; otherwise label
  `MET` or `NOT_MET` and record the evidence. The current Pexels smoke labels are
  provisional single-pass visual reviews; obtain independent project annotation
  before treating them as ground truth.
- Missing annotations, weak machine-generated labels, and uncertain licensing are
  excluded from scored cases.
- Split by image ID into `dev` and `held_out` before prompt iteration. Never tune a
  prompt against held-out results.

## JSONL manifest fields

Each non-empty line is one image request. One request can score two or three
conditions to limit API calls. Store relative paths under `AI_IMAGE_ROOT`.

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
    {"challenge_condition_id": 101, "code": "BOTTLE_VISIBLE", "condition_type": "OBJECT_VISIBLE", "description": "A water bottle is visible", "required": true, "sort_order": 1},
    {"challenge_condition_id": 102, "code": "DRINKING_VISIBLE", "condition_type": "ACTION_VISIBLE", "description": "A person is visibly drinking water", "required": true, "sort_order": 2}
  ],
  "expected_results": [
    {"challenge_condition_id": 101, "status": "MET", "label_basis": "human_verified_positive"},
    {"challenge_condition_id": 102, "status": "UNCERTAIN", "label_basis": "manual_review"}
  ]
}
```

`dataset_split` records the source dataset's split. `split` records MOAMU's `dev`
or `held_out` evaluation partition. Use synthetic placeholder IDs only in
documentation. Do not score a real case until the image's exact public dataset ID
and license have been checked.

## Metrics

- 3-way confusion matrix and macro-F1, overall and per condition code.
- False-accept rate: `NOT_MET` examples predicted `MET` divided by all scored
  `NOT_MET` examples.
- False-reject rate: `MET` examples predicted `NOT_MET` divided by all scored
  `MET` examples.
- If a run has no `NOT_MET` labels, false-accept rate is undefined and recorded as
  `null`; if it has no `MET` labels, false-reject rate is `null`.
- Coverage: predictions other than `UNCERTAIN` divided by all predictions.
- Selective accuracy: correct predictions among non-`UNCERTAIN` predictions.
- Report `UNCERTAIN` count/rate separately. Binary public labels cannot establish
  whether an `UNCERTAIN` answer is correct; that requires manually labeled
  ambiguous cases.
- Record request latency, model-reported input/output token counts, and CPU/RAM for
  Ollama. Include condition-level qualitative error categories.

The benchmark runner is deliberately dry-run by default. Gemini execution requires
`--execute` and is capped at six image cases per run; use the local Ollama provider
for broader experiments when its CPU latency is acceptable.
