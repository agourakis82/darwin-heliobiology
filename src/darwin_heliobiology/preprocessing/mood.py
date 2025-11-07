"""Normalização e fusão de escalas de humor."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np


@dataclass(slots=True)
class MoodScore:
    value: float
    label: str


MOOD_LABELS = {
    "estavel": (0.0, 0.33),
    "vigilancia": (0.33, 0.66),
    "alerta": (0.66, 1.01),
}


def normalize_likert(value: float, *, minimum: float, maximum: float) -> float:
    if maximum <= minimum:
        raise ValueError("max deve ser maior que min")
    clipped = np.clip(value, minimum, maximum)
    return float((clipped - minimum) / (maximum - minimum))


def aggregate_mood(responses: Mapping[str, float], scales: Mapping[str, Sequence[float]]) -> float:
    """Gera score único ponderando múltiplas escalas."""

    values = []
    weights = []
    for key, response in responses.items():
        if key not in scales:
            continue
        min_val, max_val = scales[key]
        values.append(normalize_likert(response, minimum=min_val, maximum=max_val))
        weights.append(1.0)
    if not values:
        raise ValueError("Nenhuma resposta suportada informada")
    return float(np.average(values, weights=weights))


def label_mood(score: float) -> str:
    for label, (lower, upper) in MOOD_LABELS.items():
        if lower <= score < upper:
            return label
    return "alerta"


def make_mood_score(
    responses: Mapping[str, float], scales: Mapping[str, Sequence[float]]
) -> MoodScore:
    score = aggregate_mood(responses, scales)
    return MoodScore(value=score, label=label_mood(score))
