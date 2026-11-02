# AI photo-verification evaluation

This directory is the maintained experiment record while the supplied Notion page
is not visible to the connected Notion integration. The page fetch returned 404,
so results are kept in Markdown and machine-readable JSON locally. Recheck Notion
access before moving records there.

## Files

- [Model selection](model-selection.md): candidates, comparison method, cost controls.
- [Prompt experiments](prompt-experiments.md): versioned prompt and sensitivity log.
- [Dataset and metrics](dataset-and-metrics.md): public data sources, labels, six goal types.
- [Six-category quantitative evaluation plan](six-category-quantitative-evaluation-plan.md): additional image sources, labeling protocol, sample size, metrics, and prompt-tuning decision gates.
- [Six-category v2/v4 pilot report](six-category-v2-pilot-20261102.md): 30 Pexels cases, Gemini results, one prompt-tuning loop, and the next evaluation gaps.
- [Benchmark run log](benchmark-log.md): durable record template and current status.
- [Six-challenge positive smoke evaluation](six-challenge-positive-smoke.md): curated image sources, two conditions per challenge, Gemini results, and limitations.
- [API contract](api-contract.md): internal endpoint contract and error mapping.

## Run a benchmark

The runner is dry-run by default. A live Gemini run requires `--execute`, reads
`GEMINI_TOKEN_API_KEY` from `.env`, and is capped at six image cases per run. Tests
use fake providers and do not make Gemini requests.

```bash
moamu-evaluate --manifest data/evaluation/manifest.jsonl --provider gemini --limit 6
moamu-evaluate --manifest data/evaluation/manifest.jsonl --provider gemini --limit 6 --execute
```

The six-challenge smoke run used three batches of six images and one focused
three-image wording retest. Its manifest and findings are in
[six-challenge-positive-smoke.md](six-challenge-positive-smoke.md).

The 2026-11-02 prompt comparison is recorded in
[six-category-v2-pilot-20261102.md](six-category-v2-pilot-20261102.md). It compares
`photo-verification-v2` and `photo-verification-v4` on the same 30 development
photos; the raw model outputs remain ignored under `data/evaluation/results/`.

Each image case evaluates two to five conditions in one model request. Run output
is written to `data/evaluation/results/`, which is ignored by Git. Image files are
kept outside the repository under the configured `AI_IMAGE_ROOT`; the manifest
stores source IDs, labels, and licenses.

Gemini calls require the explicit `--execute` flag so offline test loops cannot
spend the user's API budget. The runner limits each live execution to six images.
