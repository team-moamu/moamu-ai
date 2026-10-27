# Benchmark run log

This is the durable Markdown fallback for the requested Notion experiment page.
The connected Notion integration returned a 404 even after the page was shared, so
no Notion write was made. This file remains the source of record until access works.

## Run entry template

Copy this section for each run. One run is one provider/model × prompt version ×
dataset revision/split combination.

```markdown
### Run <run-id>

- Started at (UTC):
- Provider:
- Model ID/tag and digest:
- SDK/runtime version:
- Hardware/OS (CPU/RAM for Ollama):
- Prompt version and SHA-256:
- Dataset revision and split:
- Cases / image calls:
- Input / output / total tokens:
- Estimated cost (USD, price snapshot date):
- p50 / p95 latency:
- Accuracy / macro-F1:
- False-accept rate:
- False-reject rate:
- UNCERTAIN rate / coverage / selective accuracy:
- Decision:
- Qualitative review and case IDs:

| GoalTemplate | N | MET precision/recall | False accept | False reject | UNCERTAIN | Coverage | Error notes |
|---|---:|---:|---:|---:|---:|---:|---|
| STUDY_REVIEW | | | | | | | |
| STAIRS_EXERCISE | | | | | | | |
| WATER_INTAKE | | | | | | | |
| ALGORITHM_STUDY | | | | | | | |
| SUPPLEMENT_INTAKE | | | | | | | |
| BADGE_CARRY | | | | | | | |
```

## Run 3d91077d-0b9b-4818-a673-159d7a2bed6a — Open Images smoke test

- Started at (UTC): `2026-10-27T14:30:21Z`
- Provider/model: Gemini API / `gemini-3.5-flash-lite`
- SDK/runtime: `google-genai 1.75.0`, Python `3.13.5`
- Hardware: macOS 26.3.1, arm64 (cloud inference; local hardware does not run the model)
- Prompt: `photo-verification-v1`; template SHA-256 `bba158afbae14bd5072c28d2b562d1220627d1efccd92ed88aececd2cf3c2302`
- Dataset: Open Images V7 validation subset, development partition, image ID
  `7b14d1d7166f9abd`; Google/Crowdsource-verified positive labels for Bottle and Person
- Image: 640×480 convenience thumbnail; SHA-256
  `04ef545876b44ce93de86ad211d6ba2b8c771344329811bd65fd67fafaaf2f13`
- Attribution: “08.01.nigel hair” by `dolce_evita`, CC BY 2.0; [Flickr source](https://www.flickr.com/photos/astridge/5335975004)
- Cases / image calls / conditions: `1 / 1 / 2`
- Input / output / total tokens: `1,276 / 68 / 1,344`
- Estimated cost: `$0.0005528` using the `2026-10-26` standard-price snapshot; this is an estimate, not billing data
- p50 / p95 latency: `2,939.42 ms / 2,939.42 ms`
- Results: `BOTTLE_VISIBLE MET` (expected MET); `PERSON_VISIBLE MET` (expected MET)
- Metrics: accuracy `2/2`; macro-F1 `1.0`; false-reject rate `0/2`; `UNCERTAIN` `0/2`; coverage `2/2`
- False-accept rate: not measurable because this case has no labeled `NOT_MET` conditions
- Decision: smoke test confirms one structured Gemini request works. This is not evidence for the six MOAMU goal templates or the PRD's false-accept/acceptance targets.

The image and raw JSON result stay in ignored local paths under `data/images/` and
`data/evaluation/results/`. The one-line manifest is committed at
`data/evaluation/open-images-v7-smoke.jsonl` so the case and labels can be
reproduced after obtaining the source image. Initial attempts exposed unsupported
Gemini schema fields; those requests returned no model result and are not scored.

## Current status

- One Open Images V7 object-presence case and 18 manually selected Pexels
  positive photos have been evaluated with Gemini. The six-challenge results and
  condition wording retest are recorded in
  [six-challenge-positive-smoke.md](six-challenge-positive-smoke.md).
- The benchmark runner defaults to dry-run and caps Gemini at six image calls per
  execution. It records no image bytes and keeps generated result files ignored.
- The six-challenge set contains only positive examples. More cases are needed,
  especially explicit negatives and manually labeled ambiguous examples, before
  false-accept metrics, model comparison, or PRD target claims are meaningful.

## Run 2026-10-27 — Six challenge positive smoke set

- Manifest: `data/evaluation/six-challenge-positive-20261027.jsonl` (18 cases,
  36 manually reviewed positive condition labels). Original supplement wording is
  preserved in `data/evaluation/six-challenge-positive-v1-20261027.jsonl`.
- Source: 18 Pexels photos, resized to 640px and kept only in ignored local image
  paths. The per-image creator, source page, license, and SHA-256 are recorded in
  [the evaluation details](six-challenge-positive-smoke.md).
- Provider/model: Gemini API / `gemini-3.5-flash-lite`.
- Stable prompt: `photo-verification-v1`; the supplemental retest changed only
  the supplement condition description.
- Calls: 18 across three six-image runs, then 3 focused supplement retest calls;
  21 total image calls, 42 condition predictions.
- Initial result: 35/36 conditions `MET`, 1/36 `NOT_MET`, 0 `UNCERTAIN`. The
  rejected condition asked for pills outside the container, but the positive
  photo showed them inside a clear vial.
- Retest: after changing the condition to include visible pills inside or
  outside the container, the three supplement photos returned 6/6 `MET`.
- Effective final positive set: 36/36 `MET`. This set has no negative or
  uncertain examples, so false-accept rate is not measurable.
- Tokens: 27,751 input; 1,366 output; 29,117 total across all 21 calls.
- Estimated cost: `$0.0117403` at the current standard paid token prices; not a
  billing receipt. Aggregate p50/p95 latency: `1,819.25 / 2,869.04 ms`.
- Raw JSON outputs remain ignored under `data/evaluation/results/`; run IDs and
  per-case outcomes are preserved in the evaluation details page.
- Decision: Gemini passed this curated positive smoke set after one condition
  phrase was clarified. This does not establish general performance or satisfy
  the false-accept target; add hard negatives and ambiguous examples next.
