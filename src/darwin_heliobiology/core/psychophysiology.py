"""Transformações psicofisiológicas para dados públicos."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

import numpy as np


@dataclass(slots=True)
class AutonomicSnapshot:
    """Agrupa métricas autonômicas derivadas de datasets públicos (ex.: HRV)."""

    rmssd_ms: float
    sdnn_ms: float
    heart_rate_bpm: float

    def normalized_sensitivity(self) -> float:
        """Sensibilidade geomagnética estimada (0..1)."""

        baseline = max(self.rmssd_ms, 1.0)
        scale = np.clip(1 - (baseline / 100.0), 0.0, 1.0)
        circadian_penalty = np.clip((self.sdnn_ms - 50) / 100.0, -1.0, 1.0)
        return float(np.clip(scale + circadian_penalty * 0.2, 0.0, 1.0))


def aggregate_hrv_series(series: Iterable[float]) -> AutonomicSnapshot:
    """Gera snapshot autonômico a partir de série de RR-intervals (ms)."""

    values = np.asarray(list(series), dtype=float)
    if values.size == 0:
        raise ValueError("Série HRV vazia")

    rmssd = float(np.sqrt(np.mean(np.square(np.diff(values)))))
    sdnn = float(np.std(values, ddof=1))
    mean_rr = float(np.mean(values))
    hr_bpm = 60000.0 / mean_rr if mean_rr else 0.0

    return AutonomicSnapshot(rmssd_ms=rmssd, sdnn_ms=sdnn, heart_rate_bpm=hr_bpm)


def mood_normalization(scores: Dict[str, float]) -> Dict[str, float]:
    """Normaliza escalas clínicas (PHQ-9, GAD-7) para 0..1."""

    normalized: Dict[str, float] = {}
    for key, value in scores.items():
        if key.lower().startswith("phq"):
            normalized[key] = float(np.clip(value / 27.0, 0.0, 1.0))
        elif key.lower().startswith("gad"):
            normalized[key] = float(np.clip(value / 21.0, 0.0, 1.0))
        else:
            normalized[key] = float(np.clip(value, 0.0, 1.0))
    return normalized


def merge_multimodal(observation: Dict[str, float], mood: Dict[str, float]) -> List[float]:
    """Concatena variáveis geomagnéticas e clínicas em embedding simples."""

    geomag = [observation.get("kp", 0.0), observation.get("dst", 0.0), observation.get("bz", 0.0)]
    mood_vector = list(mood.values())
    return geomag + mood_vector



