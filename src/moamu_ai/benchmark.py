import argparse
import hashlib
import json
import math
from collections.abc import Iterable
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4

from pydantic import ValidationError

from moamu_ai.config import Settings
from moamu_ai.metrics import summarize_cases
from moamu_ai.prompts import PROMPT_VERSION, VERIFICATION_INSTRUCTION, build_verification_prompt
from moamu_ai.providers.base import PhotoJudge
from moamu_ai.providers.factory import create_photo_judge
from moamu_ai.schemas import BenchmarkCase, PhotoVerificationRequest
from moamu_ai.service import PhotoVerificationService

GEMINI_PRICE_SNAPSHOT_DATE = "2026-10-26"
GEMINI_PRICE_SOURCE = "https://ai.google.dev/gemini-api/docs/pricing"
GEMINI_STANDARD_USD_PER_MILLION_TOKENS = {"gemini-3.5-flash-lite": {"input": 0.30, "output": 2.50}}


def load_manifest(path: Path) -> list[BenchmarkCase]:
    cases: list[BenchmarkCase] = []
    seen_case_ids = set()
    with Path(path).open("r", encoding="utf-8") as manifest:
        for line_number, line in enumerate(manifest, start=1):
            if not line.strip():
                continue
            try:
                case = BenchmarkCase.model_validate_json(line)
            except ValidationError as exc:
                raise ValueError(f"invalid manifest line {line_number}: {exc}") from exc
            if case.case_id in seen_case_ids:
                raise ValueError(f"duplicate case_id on line {line_number}: {case.case_id}")
            seen_case_ids.add(case.case_id)
            cases.append(case)
    return cases


def validate_run_limit(limit: int, provider: str, max_gemini_calls: int = 6) -> None:
    if limit < 1:
        raise ValueError("limit must be at least one case")
    if provider == "gemini" and limit > min(max_gemini_calls, 6):
        raise ValueError("Gemini benchmark maximum is 6 calls per run")


def estimate_cost_usd(model: str, prompt_tokens, output_tokens) -> Optional[float]:
    prices = GEMINI_STANDARD_USD_PER_MILLION_TOKENS.get(model)
    if prices is None or prompt_tokens is None or output_tokens is None:
        return None
    return round(
        (prompt_tokens * prices["input"] + output_tokens * prices["output"]) / 1_000_000,
        8,
    )


def _percentile(values: list[float], percentile: float) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    position = percentile * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    value = ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)
    return round(value, 2)


def compare_prompt_runs(previous: dict, current: dict) -> dict:
    """Compare predictions from two saved benchmark runs without calling a model."""
    for field in ("provider", "models"):
        if previous.get(field) != current.get(field):
            raise ValueError(f"prompt runs must use the same {field}")

    def predictions(run: dict) -> tuple[set[str], dict[tuple[str, int], dict]]:
        case_ids = set()
        indexed = {}
        for case in run.get("cases", []):
            case_id = case["case_id"]
            if case_id in case_ids:
                raise ValueError(f"duplicate case_id in prompt run: {case_id}")
            case_ids.add(case_id)
            for item in case.get("condition_results", []):
                key = (case_id, item["challenge_condition_id"])
                if key in indexed:
                    raise ValueError(f"duplicate prediction for {key}")
                indexed[key] = item
        return case_ids, indexed

    previous_case_ids, before = predictions(previous)
    current_case_ids, after = predictions(current)
    if previous_case_ids != current_case_ids or before.keys() != after.keys():
        raise ValueError("prompt runs must contain the same case and condition IDs")

    previous_cases = {case["case_id"]: case for case in previous.get("cases", [])}
    current_cases = {case["case_id"]: case for case in current.get("cases", [])}
    for case_id in previous_case_ids:
        for field in (
            "goal_template_code",
            "dataset_name",
            "dataset_version",
            "dataset_image_id",
            "image_license",
            "split",
        ):
            if previous_cases[case_id].get(field) != current_cases[case_id].get(field):
                raise ValueError(f"prompt runs must use the same {field}")

    changed = []
    labeled_count = 0
    negative_count = 0
    false_accepts_before = false_accepts_after = 0
    uncertain_before = uncertain_after = 0
    for case_id, condition_id in sorted(before):
        left = before[(case_id, condition_id)]
        right = after[(case_id, condition_id)]
        if left.get("expected_status") != right.get("expected_status"):
            raise ValueError("prompt runs must use the same expected labels")
        expected_status = left.get("expected_status")
        if expected_status is not None:
            labeled_count += 1
            if expected_status == "NOT_MET":
                negative_count += 1
                false_accepts_before += left["predicted_status"] == "MET"
                false_accepts_after += right["predicted_status"] == "MET"
        uncertain_before += left["predicted_status"] == "UNCERTAIN"
        uncertain_after += right["predicted_status"] == "UNCERTAIN"
        if left["predicted_status"] != right["predicted_status"]:
            changed.append(
                {
                    "case_id": case_id,
                    "challenge_condition_id": condition_id,
                    "expected_status": left.get("expected_status"),
                    "previous_status": left["predicted_status"],
                    "current_status": right["predicted_status"],
                }
            )

    count = len(before)
    previous_false_accept_rate = false_accepts_before / negative_count if negative_count else None
    current_false_accept_rate = false_accepts_after / negative_count if negative_count else None
    return {
        "previous_run_id": previous.get("run_id"),
        "current_run_id": current.get("run_id"),
        "previous_prompt_version": previous.get("prompt_version"),
        "current_prompt_version": current.get("prompt_version"),
        "previous_prompt_template_sha256": previous.get("prompt_template_sha256"),
        "current_prompt_template_sha256": current.get("prompt_template_sha256"),
        "compared_predictions": count,
        "changed_predictions": len(changed),
        "status_flip_rate": (len(changed) / count) if count else 0.0,
        "labeled_predictions": labeled_count,
        "previous_false_accept_rate": previous_false_accept_rate,
        "current_false_accept_rate": current_false_accept_rate,
        "false_accept_rate_delta": (
            current_false_accept_rate - previous_false_accept_rate
            if previous_false_accept_rate is not None
            else None
        ),
        "previous_uncertain_count": uncertain_before,
        "current_uncertain_count": uncertain_after,
        "uncertain_count_delta": uncertain_after - uncertain_before,
        "previous_uncertain_rate": (uncertain_before / count) if count else 0.0,
        "current_uncertain_rate": (uncertain_after / count) if count else 0.0,
        "uncertain_rate_delta": ((uncertain_after - uncertain_before) / count if count else 0.0),
        "changed": changed,
    }


def run_benchmark(
    cases: Iterable[BenchmarkCase],
    judge: PhotoJudge,
    image_root: Path,
    provider: str,
    limit: int = 6,
    max_gemini_calls: int = 6,
) -> dict:
    validate_run_limit(limit, provider, max_gemini_calls=max_gemini_calls)
    selected = list(cases)[:limit]
    if provider == "gemini" and len(selected) > max_gemini_calls:
        raise ValueError("Gemini benchmark maximum is 6 calls per run")

    service = PhotoVerificationService(lambda: judge, image_root)
    started_at = datetime.now(timezone.utc).isoformat()
    evaluation_rows = []
    metric_cases = []
    estimated_costs = []
    cost_is_complete = True
    latencies = []
    prompt_token_counts = []
    output_token_counts = []
    total_token_counts = []
    models = set()
    for case in selected:
        request = PhotoVerificationRequest(
            image_path=case.image_path,
            conditions=case.conditions,
        )
        response, usage = service.verify_with_usage(request)
        prompt_hash = hashlib.sha256(
            build_verification_prompt(case.conditions).encode("utf-8")
        ).hexdigest()
        estimated_cost = estimate_cost_usd(
            usage.model,
            usage.prompt_tokens,
            usage.output_tokens,
        )
        if estimated_cost is not None:
            estimated_costs.append(estimated_cost)
        else:
            cost_is_complete = False
        latencies.append(usage.latency_ms)
        models.add(usage.model)
        if usage.prompt_tokens is not None:
            prompt_token_counts.append(usage.prompt_tokens)
        if usage.output_tokens is not None:
            output_token_counts.append(usage.output_tokens)
        if usage.total_tokens is not None:
            total_token_counts.append(usage.total_tokens)
        results_by_id = {result.challenge_condition_id: result for result in response.results}
        expected_by_id = {
            expected.challenge_condition_id: expected for expected in case.expected_results
        }
        compared_results = []
        for condition in case.conditions:
            predicted = results_by_id[condition.challenge_condition_id]
            expected = expected_by_id.get(condition.challenge_condition_id)
            expected_status = expected.status.value if expected else None
            if expected is not None:
                metric_cases.append((condition.code, expected.status, predicted.status))
            compared_results.append(
                {
                    "challenge_condition_id": condition.challenge_condition_id,
                    "condition_code": condition.code,
                    "expected_status": expected_status,
                    "predicted_status": predicted.status.value,
                    "label_basis": expected.label_basis if expected else None,
                }
            )
        evaluation_rows.append(
            {
                "case_id": case.case_id,
                "goal_template_code": case.goal_template_code,
                "dataset_name": case.dataset_name,
                "dataset_version": case.dataset_version,
                "dataset_image_id": case.dataset_image_id,
                "image_license": case.image_license,
                "image_source_url": case.image_source_url,
                "split": case.split,
                "condition_results": compared_results,
                "usage": asdict(usage),
                "prompt_sha256": prompt_hash,
                "estimated_cost_usd": estimated_cost,
            }
        )

    return {
        "run_id": str(uuid4()),
        "started_at": started_at,
        "provider": provider,
        "models": sorted(models),
        "prompt_version": PROMPT_VERSION,
        "prompt_template_sha256": hashlib.sha256(
            VERIFICATION_INSTRUCTION.encode("utf-8")
        ).hexdigest(),
        "pricing_snapshot_date": GEMINI_PRICE_SNAPSHOT_DATE,
        "pricing_source": GEMINI_PRICE_SOURCE,
        "estimated_cost_usd": (
            round(sum(estimated_costs), 8) if cost_is_complete and evaluation_rows else None
        ),
        "case_limit": limit,
        "case_count": len(evaluation_rows),
        "image_calls": len(evaluation_rows),
        "token_totals": {
            "prompt": sum(prompt_token_counts) if prompt_token_counts else None,
            "output": sum(output_token_counts) if output_token_counts else None,
            "total": sum(total_token_counts) if total_token_counts else None,
        },
        "latency_ms": {
            "p50": _percentile(latencies, 0.50),
            "p95": _percentile(latencies, 0.95),
        },
        "metrics": asdict(summarize_cases(metric_cases)),
        "cases": evaluation_rows,
    }


def compare_main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Compare saved prompt benchmark runs")
    parser.add_argument("previous", type=Path)
    parser.add_argument("current", type=Path)
    args = parser.parse_args(argv)
    previous = json.loads(args.previous.read_text(encoding="utf-8"))
    current = json.loads(args.current.read_text(encoding="utf-8"))
    print(json.dumps(compare_prompt_runs(previous, current), ensure_ascii=False, indent=2))
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run a bounded photo-verification benchmark")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--provider", choices=["gemini", "ollama"])
    parser.add_argument("--limit", type=int, default=6)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Make model calls; omitted by default",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    cases = load_manifest(args.manifest)
    settings = Settings()
    provider = args.provider or settings.ai_provider
    validate_run_limit(
        args.limit,
        provider,
        max_gemini_calls=settings.gemini_max_live_calls_per_run,
    )
    if not args.execute:
        print(
            f"Dry run: manifest has {len(cases)} case(s); "
            f"up to {min(args.limit, len(cases))} would run. No model calls were made."
        )
        return 0

    selected_settings = settings.model_copy(update={"ai_provider": provider})
    judge = create_photo_judge(selected_settings)
    result = run_benchmark(
        cases=cases,
        judge=judge,
        image_root=settings.ai_image_root,
        provider=provider,
        limit=args.limit,
        max_gemini_calls=settings.gemini_max_live_calls_per_run,
    )
    output_path = args.output or Path("data/evaluation/results") / f"{result['run_id']}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {result['case_count']} case result(s) to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
