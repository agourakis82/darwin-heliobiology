"""Funções utilitárias para extração de métricas HRV."""

from __future__ import annotations

from dataclasses import dataclass
from math import log
from typing import Iterable, Sequence

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]


@dataclass(slots=True)
class HRVFeatures:
    """Conjunto mínimo de métricas HRV."""

    rmssd: float
    sdnn: float
    pnn50: float
    mean_hr: float
    median_rr: float
    sample_entropy: float


def _to_numpy_rr(rr_intervals_ms: Sequence[float] | NDArray[np.float64]) -> FloatArray:
    values = np.asarray(rr_intervals_ms, dtype=np.float64)
    if values.ndim != 1:
        raise ValueError("RR intervals devem ser unidimensionais")
    if values.size < 2:
        raise ValueError("É necessário pelo menos 2 intervalos RR")
    return values


def compute_rmssd(rr: FloatArray) -> float:
    diff = np.diff(rr)
    return float(np.sqrt(np.mean(np.square(diff))))


def compute_sdnn(rr: FloatArray) -> float:
    return float(np.std(rr, ddof=1))


def compute_pnn50(rr: FloatArray) -> float:
    diff = np.abs(np.diff(rr))
    return float(np.mean(diff > 50.0))


def compute_mean_hr(rr: FloatArray) -> float:
    mean_rr = np.mean(rr)
    return float(60_000.0 / mean_rr)


def compute_sample_entropy(rr: FloatArray, m: int = 2, tolerance: float | None = None) -> float:
    """Calcula Sample Entropy (SampEn) com fallback para sequências curtas."""

    if rr.size < m + 2:
        return 0.0

    if tolerance is None:
        tolerance = float(0.2 * np.std(rr, ddof=1))
        if tolerance == 0:
            return 0.0
    else:
        tolerance = float(tolerance)

    def _phi(order: int) -> float:
        count = 0
        for i in range(rr.size - order):
            template = rr[i : i + order]
            for j in range(i + 1, rr.size - order + 1):
                if np.all(np.abs(template - rr[j : j + order]) <= tolerance):
                    count += 1
        return count

    c_m = _phi(m)
    c_m1 = _phi(m + 1)

    if c_m == 0 or c_m1 == 0:
        return 0.0
    return float(-log(c_m1 / c_m))


def extract_hrv_features(rr_intervals_ms: Sequence[float]) -> HRVFeatures:
    rr = _to_numpy_rr(rr_intervals_ms)
    return HRVFeatures(
        rmssd=compute_rmssd(rr),
        sdnn=compute_sdnn(rr),
        pnn50=compute_pnn50(rr),
        mean_hr=compute_mean_hr(rr),
        median_rr=float(np.median(rr)),
        sample_entropy=compute_sample_entropy(rr),
    )


def rolling_window_features(
    rr_streams: Iterable[Sequence[float]],
) -> Iterable[HRVFeatures]:
    """Aplica :func:`extract_hrv_features` sobre uma sequência de janelas."""

    for window in rr_streams:
        yield extract_hrv_features(window)
