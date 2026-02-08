"""Testes para o KairosForecaster."""

import numpy as np

from darwin_heliobiology.core.psychophysiology import AutonomicSnapshot
from darwin_heliobiology.models.solar import SolarIndex
from darwin_heliobiology.services.kairos_forecaster import KairosForecaster


def _series(values):
    return [SolarIndex(timestamp=None, value=v, label="Kp") for v in values]


def test_forecaster_generates_risk_projection():
    kp_series = _series([3.0, 4.5, 6.0])
    dst_series = [SolarIndex(timestamp=None, value=v, label="Dst") for v in [-10.0, -30.0, -70.0]]

    forecaster = KairosForecaster(smoothing_factor=0.5)
    forecaster.fit(kp_series, dst_series)

    snapshot = AutonomicSnapshot(rmssd_ms=45.0, sdnn_ms=60.0, heart_rate_bpm=75.0)
    result = forecaster.forecast(steps=3, snapshot=snapshot)

    assert result.kp_forecast.shape == (3,)
    assert result.dst_forecast.shape == (3,)
    assert np.all(result.risk_projection >= 0)
    assert np.all(result.risk_projection <= 1)
