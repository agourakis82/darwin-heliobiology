from __future__ import annotations

from darwin_heliobiology.preprocessing.mood import MOOD_LABELS, make_mood_score, normalize_likert


def test_normalize_likert_bounds():
    assert normalize_likert(3, minimum=1, maximum=5) == 0.5


def test_make_mood_score_combines_scales():
    responses = {"PANAS_pos": 4, "PANAS_neg": 2}
    scales = {"PANAS_pos": (1, 5), "PANAS_neg": (1, 5)}
    score = make_mood_score(responses, scales)
    assert 0 <= score.value <= 1
    assert score.label in MOOD_LABELS
