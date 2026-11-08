from moamu_ai.metrics import summarize_cases


def test_metrics_track_false_accepts_abstention_and_coverage():
    """오수락, 불확실 응답, 판정 범위 지표를 확인한다."""
    summary = summarize_cases(
        [
            ("WATER", "MET", "MET"),
            ("WATER", "NOT_MET", "MET"),
            ("WATER", "MET", "UNCERTAIN"),
            ("STUDY", "NOT_MET", "NOT_MET"),
        ]
    )

    assert summary.total_cases == 4
    assert summary.false_accepts == 1
    assert summary.uncertain_predictions == 1
    assert summary.coverage == 0.75
    assert summary.false_accept_rate == 0.5
    assert summary.false_reject_rate == 0.0
    assert summary.by_condition["WATER"].false_accepts == 1
    assert summary.by_condition["STUDY"].accuracy == 1.0


def test_macro_f1_includes_a_class_that_appears_only_in_predictions():
    """예측에만 나타난 클래스도 macro F1에 포함하는지 확인한다."""
    summary = summarize_cases(
        [
            ("WATER", "NOT_MET", "NOT_MET"),
            ("WATER", "NOT_MET", "MET"),
        ]
    )

    assert summary.macro_f1 == 1 / 3


def test_class_rates_are_undefined_without_reference_examples_for_their_denominator():
    """분모에 해당하는 정답이 없을 때 비율을 정의하지 않는지 확인한다."""
    positive_only = summarize_cases([("BOTTLE", "MET", "MET")])
    negative_only = summarize_cases([("BOTTLE", "NOT_MET", "NOT_MET")])

    assert positive_only.false_accept_rate is None
    assert positive_only.false_reject_rate == 0.0
    assert negative_only.false_accept_rate == 0.0
    assert negative_only.false_reject_rate is None
