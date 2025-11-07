from __future__ import annotations

import numpy as np

from darwin_heliobiology.features.hrv import (
    compute_mean_hr,
    compute_pnn50,
    compute_rmssd,
    compute_sdnn,
    extract_hrv_features,
)


def test_rmssd_sdnn_computation():
    rr = np.array([800, 820, 780, 790, 810], dtype=float)
    rmssd = compute_rmssd(rr)
    sdnn = compute_sdnn(rr)
    assert rmssd > 0
    assert sdnn > 0


def test_pnn50_and_mean_hr():
    rr = np.array([1000, 960, 940, 920, 900], dtype=float)
    assert 0 <= compute_pnn50(rr) <= 1
    assert 60 <= compute_mean_hr(rr) <= 70


def test_extract_hrv_features_returns_dataclass():
    rr = [900.0, 910.0, 890.0, 905.0]
    features = extract_hrv_features(rr)
    assert features.rmssd > 0
    assert features.mean_hr > 60
