import json
from pathlib import Path

import pytest

from moamu_ai.benchmark import (
    compare_prompt_runs,
    estimate_cost_usd,
    load_manifest,
    main,
    run_benchmark,
    validate_run_limit,
)
from moamu_ai.providers.base import InferenceResult, InferenceUsage
from moamu_ai.schemas import BenchmarkCase, ConditionResult, ConditionStatus


class FakeJudge:
    def __init__(self):
        self.calls = 0

    def evaluate(self, image_path, conditions):
        self.calls += 1
        return InferenceResult(
            results=[
                ConditionResult(
                    challenge_condition_id=item.challenge_condition_id,
                    status=(
                        ConditionStatus.MET
                        if item.challenge_condition_id == 1
                        else ConditionStatus.NOT_MET
                    ),
                )
                for item in conditions
            ],
            usage=InferenceUsage(
                model="qwen3-vl:2b",
                latency_ms=250,
                prompt_tokens=100,
                output_tokens=10,
                total_tokens=110,
            ),
        )


def sample_case(image_path: str):
    return {
        "case_id": "open-images-sample-1",
        "goal_template_code": "WATER_INTAKE",
        "dataset_name": "Open Images V7",
        "dataset_version": "v7",
        "dataset_split": "validation",
        "dataset_image_id": "sample-image-id",
        "image_license": "CC BY 2.0 (verify per image)",
        "split": "dev",
        "image_path": image_path,
        "conditions": [
            {
                "challenge_condition_id": 1,
                "code": "BOTTLE_VISIBLE",
                "condition_type": "OBJECT_VISIBLE",
                "description": "A water bottle is visible",
                "required": True,
                "sort_order": 1,
            },
            {
                "challenge_condition_id": 2,
                "code": "DRINKING_VISIBLE",
                "condition_type": "ACTION_VISIBLE",
                "description": "A person is visibly drinking water",
                "required": True,
                "sort_order": 2,
            },
        ],
        "expected_results": [
            {
                "challenge_condition_id": 1,
                "status": "MET",
                "label_basis": "human_verified_positive",
            },
            {
                "challenge_condition_id": 2,
                "status": "NOT_MET",
                "label_basis": "human_verified_negative",
            },
        ],
    }


def test_manifest_runner_records_outputs_and_per_condition_metrics(tmp_path: Path):
    image_root = tmp_path / "images"
    image_root.mkdir()
    (image_root / "sample.jpg").write_bytes(b"test image")
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text(json.dumps(sample_case("sample.jpg")) + "\n")
    cases = load_manifest(manifest)
    judge = FakeJudge()

    result = run_benchmark(
        cases=cases,
        judge=judge,
        image_root=image_root,
        provider="ollama",
        limit=6,
    )

    assert judge.calls == 1
    assert result["case_count"] == 1
    assert result["cases"][0]["usage"]["total_tokens"] == 110
    assert result["metrics"]["total_cases"] == 2
    assert result["metrics"]["false_accepts"] == 0
    assert result["estimated_cost_usd"] is None
    assert result["metrics"]["by_condition"]["BOTTLE_VISIBLE"]["accuracy"] == 1.0
    assert result["image_calls"] == 1
    assert result["cases"][0]["dataset_split"] == "validation"
    assert result["token_totals"] == {"prompt": 100, "output": 10, "total": 110}
    assert result["latency_ms"] == {"p50": 250, "p95": 250}
    assert len(result["cases"][0]["prompt_sha256"]) == 64
    assert "image_path" not in result["cases"][0]


def test_benchmark_records_unlabeled_predictions_but_excludes_them_from_metrics(tmp_path: Path):
    image_root = tmp_path / "images"
    image_root.mkdir()
    (image_root / "sample.jpg").write_bytes(b"test image")
    case_data = sample_case("sample.jpg")
    case_data["expected_results"] = case_data["expected_results"][:1]
    judge = FakeJudge()

    result = run_benchmark(
        cases=[BenchmarkCase.model_validate(case_data)],
        judge=judge,
        image_root=image_root,
        provider="ollama",
    )

    assert len(result["cases"][0]["condition_results"]) == 2
    assert result["cases"][0]["condition_results"][1]["expected_status"] is None
    assert result["metrics"]["total_cases"] == 1


def test_prompt_run_comparison_reports_condition_level_flip_rate():
    previous = {
        "run_id": "run-1",
        "prompt_version": "photo-verification-v1",
        "prompt_template_sha256": "a" * 64,
        "cases": [
            {
                "case_id": "case-1",
                "prompt_sha256": "a" * 64,
                "condition_results": [
                    {
                        "challenge_condition_id": 1,
                        "expected_status": "MET",
                        "predicted_status": "MET",
                    },
                    {
                        "challenge_condition_id": 2,
                        "expected_status": "NOT_MET",
                        "predicted_status": "UNCERTAIN",
                    },
                ],
            }
        ],
    }
    current = {
        "run_id": "run-2",
        "prompt_version": "photo-verification-v2",
        "prompt_template_sha256": "b" * 64,
        "cases": [
            {
                "case_id": "case-1",
                "prompt_sha256": "b" * 64,
                "condition_results": [
                    {
                        "challenge_condition_id": 1,
                        "expected_status": "MET",
                        "predicted_status": "NOT_MET",
                    },
                    {
                        "challenge_condition_id": 2,
                        "expected_status": "NOT_MET",
                        "predicted_status": "MET",
                    },
                ],
            }
        ],
    }

    comparison = compare_prompt_runs(previous, current)

    assert comparison["compared_predictions"] == 2
    assert comparison["changed_predictions"] == 2
    assert comparison["status_flip_rate"] == 1.0
    assert comparison["previous_prompt_template_sha256"] == "a" * 64
    assert comparison["false_accept_rate_delta"] == 1.0
    assert comparison["uncertain_count_delta"] == -1
    assert comparison["changed"][0]["challenge_condition_id"] == 1


def test_prompt_run_comparison_rejects_different_case_sets():
    with pytest.raises(ValueError, match="same case and condition IDs"):
        compare_prompt_runs(
            {"cases": [{"case_id": "left", "condition_results": []}]},
            {"cases": [{"case_id": "right", "condition_results": []}]},
        )


def test_manifest_rejects_expected_condition_ids_not_in_snapshot(tmp_path: Path):
    case = sample_case("sample.jpg")
    case["expected_results"][0]["challenge_condition_id"] = 999
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text(json.dumps(case) + "\n")

    with pytest.raises(ValueError, match="expected result IDs"):
        load_manifest(manifest)


def test_gemini_benchmark_limit_is_capped_at_six_calls_per_run():
    validate_run_limit(6, provider="gemini", max_gemini_calls=6)

    with pytest.raises(ValueError, match="maximum is 6"):
        validate_run_limit(7, provider="gemini", max_gemini_calls=6)


def test_cost_estimate_uses_recorded_tokens_and_unknown_models_remain_unpriced():
    assert estimate_cost_usd("gemini-3.5-flash-lite", 1000, 1000) == 0.0028
    assert estimate_cost_usd("qwen3-vl:2b", 1000, 1000) is None


def test_benchmark_cli_is_dry_run_without_execute(tmp_path: Path, monkeypatch, capsys):
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text(json.dumps(sample_case("missing.jpg")) + "\n")

    def unexpected_live_client(*args, **kwargs):
        raise AssertionError("dry-run must not create a provider client")

    monkeypatch.setattr("moamu_ai.benchmark.create_photo_judge", unexpected_live_client)

    assert main(["--manifest", str(manifest), "--provider", "gemini"]) == 0
    assert "No model calls were made" in capsys.readouterr().out
