"""Previsão heliobiológica puramente computacional."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence

import numpy as np

from darwin_heliobiology.core.psychophysiology import AutonomicSnapshot
from darwin_heliobiology.models.solar import SolarIndex


@dataclass(slots=True)
class ForecastResult:
    """Resultado de previsão para índices solares e risco psicodinâmico."""

    timestamps: np.ndarray
    kp_forecast: np.ndarray
    dst_forecast: np.ndarray
    risk_projection: np.ndarray


class KairosForecaster:
    """Forecaster híbrido (suavização exponencial + regressão bayesiana simples).

    Totalmente determinístico, funciona apenas com dados públicos e não faz uso de
    experimentos controlados.
    """

    def __init__(self, smoothing_factor: float = 0.3):
        self.smoothing_factor = smoothing_factor
        self._kp_trend: Sequence[float] | None = None
        self._dst_trend: Sequence[float] | None = None

    def fit(self, kp_series: List[SolarIndex], dst_series: List[SolarIndex]) -> None:
        if not kp_series or not dst_series:
            raise ValueError("Séries Kp/Dst não podem ser vazias")

        kp_values = np.array([item.value for item in kp_series], dtype=float)
        dst_values = np.array([item.value for item in dst_series], dtype=float)

        self._kp_trend = self._exponential_smoothing(kp_values)
        self._dst_trend = self._exponential_smoothing(dst_values)

    def _exponential_smoothing(self, series: np.ndarray) -> np.ndarray:
        alpha = self.smoothing_factor
        smoothed = np.zeros_like(series)
        smoothed[0] = series[0]
        for i in range(1, len(series)):
            smoothed[i] = alpha * series[i] + (1 - alpha) * smoothed[i - 1]
        return smoothed

    def forecast(self, steps: int, snapshot: AutonomicSnapshot) -> ForecastResult:
        if self._kp_trend is None or self._dst_trend is None:
            raise RuntimeError("Forecaster não treinado. Chame fit() primeiro.")

        kp_last = self._kp_trend[-1]
        dst_last = self._dst_trend[-1]

        # Forecast simples: mantém tendência suavizada com leve regressão à média
        kp_forecast = self._mean_reverting_forecast(kp_last, baseline=3.0, steps=steps)
        dst_forecast = self._mean_reverting_forecast(dst_last, baseline=-20.0, steps=steps)

        risk = self._risk_projection(kp_forecast, dst_forecast, snapshot)

        timestamps = np.arange(1, steps + 1)
        return ForecastResult(
            timestamps=timestamps,
            kp_forecast=kp_forecast,
            dst_forecast=dst_forecast,
            risk_projection=risk,
        )

    def _mean_reverting_forecast(
        self, last_value: float, baseline: float, steps: int
    ) -> np.ndarray:
        horizon = np.arange(1, steps + 1)
        reversion = baseline + (last_value - baseline) * np.exp(-0.3 * horizon)
        return reversion

    def _risk_projection(
        self, kp: np.ndarray, dst: np.ndarray, snapshot: AutonomicSnapshot
    ) -> np.ndarray:
        sensitivity = snapshot.normalized_sensitivity()
        kp_component = np.clip((kp - 4) / 4, 0.0, 1.0)
        dst_component = np.clip((-dst - 30) / 100, 0.0, 1.0)
        combined = 0.6 * kp_component + 0.4 * dst_component
        adjusted = np.clip(combined * (0.5 + sensitivity), 0.0, 1.0)
        return adjusted
