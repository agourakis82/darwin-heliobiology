"""Validação científica automatizada."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Tuple

import numpy as np


@dataclass(slots=True)
class ScientificExpectation:
    """Expectativa científica derivada de literatura Q1."""

    description: str
    lower: float
    upper: float


class AletheiaValidator:
    """Valida correlações geomagnéticas vs. saúde mental com dados públicos."""

    def validate_correlation(self, series_a: Iterable[float], series_b: Iterable[float], expectation: ScientificExpectation) -> Tuple[float, bool]:
        values_a = np.asarray(list(series_a), dtype=float)
        values_b = np.asarray(list(series_b), dtype=float)
        if values_a.size != values_b.size:
            raise ValueError("Séries devem possuir mesmo tamanho")

        if values_a.size < 3:
            raise ValueError("É necessário no mínimo 3 medições para avaliação")

        corr = float(np.corrcoef(values_a, values_b)[0, 1])
        within = expectation.lower <= corr <= expectation.upper
        return corr, within



