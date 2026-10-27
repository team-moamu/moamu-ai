from collections import defaultdict
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from typing import Optional

from moamu_ai.schemas import ConditionStatus

StatusPair = tuple[str, str]


def _status_value(value) -> str:
    return value.value if isinstance(value, ConditionStatus) else str(value)


@dataclass(frozen=True)
class ConditionMetrics:
    total_cases: int
    correct: int
    false_accepts: int
    false_accept_rate: Optional[float]
    false_rejects: int
    false_reject_rate: Optional[float]
    uncertain_predictions: int
    coverage: float
    accuracy: float
    selective_accuracy: float
    macro_f1: float
    confusion_matrix: dict[str, dict[str, int]]


@dataclass(frozen=True)
class MetricsSummary(ConditionMetrics):
    by_condition: dict[str, ConditionMetrics]


def _summarize(pairs: Iterable[StatusPair]) -> ConditionMetrics:
    confusion: defaultdict[str, defaultdict[str, int]] = defaultdict(lambda: defaultdict(int))
    correct = false_accepts = false_rejects = uncertain_predictions = 0
    expected_not_met = expected_met = 0
    accepted = accepted_correct = 0
    total = 0
    for expected, predicted in pairs:
        total += 1
        confusion[expected][predicted] += 1
        if expected == predicted:
            correct += 1
        if expected == "NOT_MET" and predicted == "MET":
            false_accepts += 1
        if expected == "NOT_MET":
            expected_not_met += 1
        if expected == "MET" and predicted == "NOT_MET":
            false_rejects += 1
        if expected == "MET":
            expected_met += 1
        if predicted == "UNCERTAIN":
            uncertain_predictions += 1
        else:
            accepted += 1
            if expected == predicted:
                accepted_correct += 1

    classes = [status.value for status in ConditionStatus]
    supported_classes = [
        label
        for label in classes
        if sum(confusion[label].values()) + sum(confusion[expected][label] for expected in classes)
        > 0
    ]
    class_f1 = []
    for label in supported_classes:
        true_positive = confusion[label][label]
        false_positive = sum(confusion[expected][label] for expected in classes) - true_positive
        false_negative = sum(confusion[label][predicted] for predicted in classes) - true_positive
        denominator = (2 * true_positive) + false_positive + false_negative
        class_f1.append((2 * true_positive / denominator) if denominator else 0.0)

    matrix = {
        expected: {predicted: confusion[expected][predicted] for predicted in classes}
        for expected in classes
    }
    return ConditionMetrics(
        total_cases=total,
        correct=correct,
        false_accepts=false_accepts,
        false_rejects=false_rejects,
        uncertain_predictions=uncertain_predictions,
        coverage=(accepted / total) if total else 0.0,
        accuracy=(correct / total) if total else 0.0,
        selective_accuracy=(accepted_correct / accepted) if accepted else 0.0,
        macro_f1=(sum(class_f1) / len(class_f1)) if class_f1 else 0.0,
        false_accept_rate=(false_accepts / expected_not_met) if expected_not_met else None,
        false_reject_rate=(false_rejects / expected_met) if expected_met else None,
        confusion_matrix=matrix,
    )


def summarize_cases(cases: Iterable[tuple[str, str, str]]) -> MetricsSummary:
    """Summarize (condition code, expected status, predicted status) records."""
    grouped: defaultdict[str, list[StatusPair]] = defaultdict(list)
    all_pairs = []
    for condition_code, expected, predicted in cases:
        pair = (_status_value(expected), _status_value(predicted))
        grouped[condition_code].append(pair)
        all_pairs.append(pair)

    overall = _summarize(all_pairs)
    return MetricsSummary(
        **asdict(overall),
        by_condition={code: _summarize(pairs) for code, pairs in sorted(grouped.items())},
    )
