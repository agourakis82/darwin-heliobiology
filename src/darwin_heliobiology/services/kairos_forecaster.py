"""Previsão heliobiológica puramente computacional."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import numpy as np
from numpy.typing import NDArray

from darwin_heliobiology.core.psychophysiology import AutonomicSnapshot
from darwin_heliobiology.models.solar import SolarIndex

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]


@dataclass(slots=True)
class ForecastResult:
    """Resultado de previsão para índices solares e risco psicodinâmico."""

    timestamps: IntArray
    kp_forecast: FloatArray
    dst_forecast: FloatArray
    risk_projection: FloatArray


class KairosForecaster:
    """Forecaster híbrido (suavização exponencial + regressão bayesiana simples).

    Totalmente determinístico, funciona apenas com dados públicos e não faz uso de
    experimentos controlados.
    """

    def __init__(self, smoothing_factor: float = 0.3):
        self.smoothing_factor = smoothing_factor
        self._kp_trend: Optional[FloatArray] = None
        self._dst_trend: Optional[FloatArray] = None

    def fit(self, kp_series: List[SolarIndex], dst_series: List[SolarIndex]) -> None:
        if not kp_series or not dst_series:
            raise ValueError("Séries Kp/Dst não podem ser vazias")

        kp_values = np.asarray([item.value for item in kp_series], dtype=np.float64)
        dst_values = np.asarray([item.value for item in dst_series], dtype=np.float64)

        self._kp_trend = self._exponential_smoothing(kp_values)
        self._dst_trend = self._exponential_smoothing(dst_values)

    def _exponential_smoothing(self, series: FloatArray) -> FloatArray:
        alpha = self.smoothing_factor
        smoothed = np.zeros_like(series, dtype=np.float64)
        smoothed[0] = series[0]
        for i in range(1, len(series)):
            smoothed[i] = alpha * series[i] + (1 - alpha) * smoothed[i - 1]
        return smoothed

    def forecast(self, steps: int, snapshot: AutonomicSnapshot) -> ForecastResult:
        if self._kp_trend is None or self._dst_trend is None:
            raise RuntimeError("Forecaster não treinado. Chame fit() primeiro.")

        kp_last = self._kp_trend[-1]
        dst_last = self._dst_trend[-1]

        kp_forecast = self._mean_reverting_forecast(kp_last, baseline=3.0, steps=steps)
        dst_forecast = self._mean_reverting_forecast(dst_last, baseline=-20.0, steps=steps)
        risk = self._risk_projection(kp_forecast, dst_forecast, snapshot)

        timestamps: IntArray = np.arange(1, steps + 1, dtype=np.int64)
        return ForecastResult(
            timestamps=timestamps,
            kp_forecast=kp_forecast,
            dst_forecast=dst_forecast,
            risk_projection=risk,
        )

    def _mean_reverting_forecast(
        self, last_value: float, baseline: float, steps: int
    ) -> FloatArray:
        horizon = np.arange(1, steps + 1, dtype=np.float64)
        reversion = baseline + (last_value - baseline) * np.exp(-0.3 * horizon)
        return np.asarray(reversion, dtype=np.float64)

    def _risk_projection(
        self, kp: FloatArray, dst: FloatArray, snapshot: AutonomicSnapshot
    ) -> FloatArray:
        sensitivity = snapshot.normalized_sensitivity()
        kp_component = np.asarray(np.clip((kp - 4.0) / 4.0, 0.0, 1.0), dtype=np.float64)
        dst_component = np.asarray(np.clip((-dst - 30.0) / 100.0, 0.0, 1.0), dtype=np.float64)
        combined = 0.6 * kp_component + 0.4 * dst_component
        adjusted = np.asarray(np.clip(combined * (0.5 + sensitivity), 0.0, 1.0), dtype=np.float64)
        return adjusted
