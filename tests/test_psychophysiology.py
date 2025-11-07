"""Testes para transformações psicofisiológicas."""

import numpy as np
import pytest

from darwin_heliobiology.core.psychophysiology import (
    AutonomicSnapshot,
    aggregate_hrv_series,
    merge_multimodal,
    mood_normalization,
)


def test_aggregate_hrv_series_returns_snapshot():
    rr = np.linspace(800, 900, 20)
    snapshot = aggregate_hrv_series(rr)

    assert isinstance(snapshot, AutonomicSnapshot)
    assert snapshot.heart_rate_bpm > 60
    assert snapshot.normalized_sensitivity() >= 0.0


def test_mood_normalization_handles_multiple_scales():
    normalized = mood_normalization({"phq9": 18, "gad7": 10, "custom": 0.5})

    assert normalized["phq9"] == pytest.approx(18 / 27)
    assert normalized["gad7"] == pytest.approx(10 / 21)
    assert normalized["custom"] == 0.5


def test_merge_multimodal_concatenates_vectors():
    observation = {"kp": 5.0, "dst": -40.0, "bz": -8.5}
    mood = {"phq9": 0.4, "gad7": 0.2}

    vector = merge_multimodal(observation, mood)

    assert vector[:3] == [5.0, -40.0, -8.5]
    assert len(vector) == 5

