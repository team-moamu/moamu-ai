# MOAMU AI photo verification

Internal FastAPI service for evaluating a submitted image against the frozen
condition snapshot supplied by the backend. See `docs/ai-evaluation/` for model,
prompt, and dataset evaluation records.

## Local development

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
# Only copy the template if this checkout has no existing .env.
test -f .env || cp .env.example .env
uvicorn moamu_ai.app:app --reload --host 127.0.0.1 --port 8000
```

## Offline benchmark

Use a JSONL manifest with licensed local images and reviewed condition labels. The
benchmark command validates the manifest without creating an API client by default:

```bash
moamu-evaluate --manifest data/evaluation/manifest.jsonl --provider gemini
```

To make model calls, add `--execute`; Gemini runs are limited to six image calls
per invocation. Compare saved prompt runs without additional model calls with:

```bash
moamu-compare-prompts results-v1.json results-v2.json
```

See `docs/ai-evaluation/` for model selection, dataset labeling, prompt versioning,
metrics, and the Markdown run log.
