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

## Current status

- No benchmark image manifest or labeled image files were supplied in the repository.
- No Gemini requests have been made by this implementation.
- The benchmark runner records model token usage and outputs, stores no image
  bytes, defaults to dry-run, and caps a Gemini run at six image calls.
- Do not treat this empty log as evidence that a model meets the PRD's 5% false
  acceptance or 85% acceptance targets.
