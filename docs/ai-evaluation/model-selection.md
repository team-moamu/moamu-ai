# Model selection record

**Review date:** 2026-10-26
**Status:** Candidates selected for a low-cost pilot; measured results pending.

## Candidates

| Provider | Candidate | Role | Notes |
|---|---|---|---|
| Gemini API | `gemini-3.5-flash-lite` | First cloud baseline | Current cost-conscious candidate; exact model ID is configurable and recorded per run. |
| Gemini API | `gemini-3.8-flash` | Follow-up comparison | Run only if the low-cost baseline misses the quality target. |
| Ollama | `qwen3-vl:2b` | First CPU VLM baseline | Image and text input; library lists a 1.9 GB model. Requires Ollama 0.12.7 or later. |
| Ollama | `gemma3:4b` | Optional CPU VLM comparison | Image and text input; library lists a 3.4 GB model. |

The API receives an image, so the local candidate must be a vision-language model.
Text-only Ollama models cannot make the required visual judgment. Qwen3-VL 2B is
the first local candidate because it has the smaller listed model footprint; the
actual RAM use and CPU latency still need measurement on the team's machine.

Sources: [Gemini models](https://ai.google.dev/gemini-api/docs/models),
[Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing),
[Ollama Qwen3-VL](https://ollama.com/library/qwen3-vl),
[Ollama Gemma 3](https://ollama.com/library/gemma3),
[Ollama CPU/GPU reporting](https://github.com/ollama/ollama/blob/main/docs/faq.mdx).

## Comparison method

1. Pin the full model ID or Ollama tag/digest, prompt version, dataset revision,
   split, SDK/runtime version, and date for every run.
2. Use the same cases, condition snapshots, and equivalent output schema for each
   provider. Run prompt changes against one fixed model before changing models.
3. Start with the six-case pilot limit. Each case sends one image and its two or
   three conditions in one request. Review recorded usage and actual Google AI
   Studio billing before expanding the dataset.
4. Prefer the model with the lower false-accept rate while keeping useful coverage
   and latency. Do not choose from aggregate accuracy alone.
5. Review representative false accepts, false rejects, and `UNCERTAIN` cases by
   condition type, visibility, occlusion, and image quality.

## Measures

| Area | Measure |
|---|---|
| Classification | 3-way confusion matrix, per-condition accuracy, macro-F1 |
| Safety | False accepts (`NOT_MET` ground truth predicted as `MET`) |
| Rejection | False rejects (`MET` ground truth predicted as `NOT_MET`) |
| Abstention | `UNCERTAIN` count, coverage, selective accuracy |
| Runtime | End-to-end p50/p95 latency; Ollama CPU/RAM and tokens per second |
| Cost | Input/output token counts, estimated USD using the dated price snapshot, actual billed usage |
| Qualitative | Short error category and anonymized case ID; never store image bytes or API keys |

At the time of this record, Google's standard paid price page lists Gemini 3.5
Flash-Lite at $0.30 per million input tokens (including image tokens) and $2.50
per million output tokens. Prices and free-tier access can change; the run log
must include the pricing check date. The code records token usage and limits each
Gemini benchmark invocation to six calls. It does not claim a cumulative KRW cap,
so review the provider's billing page before repeated runs.

## Results

| Model | Prompt | Dataset | Cases | False accept | Macro-F1 | Coverage | p50/p95 | Cost | Decision |
|---|---|---|---:|---:|---:|---:|---:|---:|---|
| Pending | `photo-verification-v1` | Open Images / MOAMU labeled pilot | 0 | — | — | — | — | — | No live calls run |
