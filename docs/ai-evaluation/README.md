# AI photo-verification evaluation

This directory is the maintained experiment record while the supplied Notion page
is not visible to the connected Notion integration. The page fetch returned 404,
so results are kept in Markdown and machine-readable JSON locally. Recheck Notion
access before moving records there.

## Files

- [Model selection](model-selection.md): candidates, comparison method, cost controls.
- [Prompt experiments](prompt-experiments.md): versioned prompt and sensitivity log.
- [Dataset and metrics](dataset-and-metrics.md): public data sources, labels, six goal types.
- [Benchmark run log](benchmark-log.md): durable record template and current status.
- [API contract](api-contract.md): internal endpoint contract and error mapping.

## Run a benchmark

The runner is dry-run by default. A live Gemini run requires `--execute`, reads
`GEMINI_TOKEN_API_KEY` from `.env`, and is capped at six image cases per run. Tests
use fake providers and do not make Gemini requests.

```bash
moamu-evaluate --manifest data/evaluation/manifest.jsonl --provider gemini --limit 6
moamu-evaluate --manifest data/evaluation/manifest.jsonl --provider gemini --limit 6 --execute
```

Each image case evaluates two or three conditions in one model request. Run output
is written to `data/evaluation/results/`, which is ignored by Git. Image files are
kept outside the repository under the configured `AI_IMAGE_ROOT`; the manifest
stores source IDs, labels, and licenses.

No live Gemini benchmark has been run in this implementation. The live flag is
deliberately explicit so local test loops cannot spend the user's API budget.
