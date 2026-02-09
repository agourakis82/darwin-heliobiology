"""Validação científica automatizada e metaanálise."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

import numpy as np
from scipy import stats as scipy_stats


@dataclass(slots=True)
class ScientificExpectation:
    """Expectativa científica derivada de literatura Q1."""

    description: str
    lower: float
    upper: float


@dataclass(slots=True)
class StudyEffect:
    """Tamanho de efeito de um estudo individual para metaanálise."""

    study_id: str
    effect_size: float
    variance: float
    n: int
    label: str


@dataclass(slots=True)
class MetaAnalysisResult:
    """Resultado de metaanálise de efeitos aleatórios (DerSimonian-Laird)."""

    pooled_effect: float
    pooled_ci_lower: float
    pooled_ci_upper: float
    tau_squared: float
    q_statistic: float
    i_squared: float
    z_score: float
    p_value: float
    studies: List[StudyEffect]
    weights: List[float]


class AletheiaValidator:
    """Valida correlações geomagnéticas vs. saúde mental com dados públicos."""

    def validate_correlation(
        self,
        series_a: Iterable[float],
        series_b: Iterable[float],
        expectation: ScientificExpectation,
    ) -> Tuple[float, bool]:
        values_a = np.asarray(list(series_a), dtype=float)
        values_b = np.asarray(list(series_b), dtype=float)
        if values_a.size != values_b.size:
            raise ValueError("Séries devem possuir mesmo tamanho")

        if values_a.size < 3:
            raise ValueError("É necessário no mínimo 3 medições para avaliação")

        corr = float(np.corrcoef(values_a, values_b)[0, 1])
        within = expectation.lower <= corr <= expectation.upper
        return corr, within

    # ------------------------------------------------------------------
    # Metaanálise automatizada
    # ------------------------------------------------------------------

    @staticmethod
    def fisher_z_transform(r: float, n: int, study_id: str = "", label: str = "") -> StudyEffect:
        """Converte correlação de Pearson *r* em Fisher-z com variância 1/(n-3)."""
        if n < 4:
            raise ValueError("É necessário n >= 4 para a transformação Fisher-z")
        z = 0.5 * math.log((1 + r) / (1 - r))
        variance = 1.0 / (n - 3)
        return StudyEffect(
            study_id=study_id,
            effect_size=z,
            variance=variance,
            n=n,
            label=label,
        )

    @staticmethod
    def inverse_fisher_z(z: float) -> float:
        """Converte Fisher-z de volta para correlação de Pearson."""
        return float(math.tanh(z))

    def meta_analyze(
        self,
        studies: List[StudyEffect],
        confidence: float = 0.95,
    ) -> MetaAnalysisResult:
        """Metaanálise de efeitos aleatórios via DerSimonian-Laird.

        Parameters
        ----------
        studies:
            Lista de efeitos individuais (já transformados, e.g. Fisher-z).
        confidence:
            Nível de confiança para o intervalo (default 0.95).

        Returns
        -------
        MetaAnalysisResult
            Efeito combinado, heterogeneidade (Q, I², τ²) e pesos.
        """
        if not studies:
            raise ValueError("É necessário pelo menos 1 estudo")

        k = len(studies)
        yi = np.asarray([s.effect_size for s in studies], dtype=np.float64)
        vi = np.asarray([s.variance for s in studies], dtype=np.float64)

        # Pesos de efeitos fixos
        wi = 1.0 / vi

        # Efeito fixo (para calcular Q)
        pooled_fe = float(np.sum(wi * yi) / np.sum(wi))

        # Cochran's Q
        q_stat = float(np.sum(wi * np.square(yi - pooled_fe)))

        # DerSimonian-Laird tau²
        c = float(np.sum(wi) - np.sum(np.square(wi)) / np.sum(wi))
        tau_sq = max(0.0, (q_stat - (k - 1)) / c) if c > 0 else 0.0

        # I² (0..100)
        i_sq = max(0.0, (q_stat - (k - 1)) / q_stat * 100.0) if q_stat > 0 else 0.0

        # Pesos de efeitos aleatórios
        wi_re = 1.0 / (vi + tau_sq)
        weights_list = [float(w) for w in wi_re]

        # Efeito combinado (random effects)
        pooled_re = float(np.sum(wi_re * yi) / np.sum(wi_re))
        se_re = float(np.sqrt(1.0 / np.sum(wi_re)))

        # Z-score e p-value
        z_score = pooled_re / se_re if se_re > 0 else 0.0
        p_value = float(2.0 * (1.0 - scipy_stats.norm.cdf(abs(z_score))))

        # Intervalo de confiança
        alpha = 1.0 - confidence
        z_crit = float(scipy_stats.norm.ppf(1.0 - alpha / 2.0))
        ci_lower = pooled_re - z_crit * se_re
        ci_upper = pooled_re + z_crit * se_re

        return MetaAnalysisResult(
            pooled_effect=pooled_re,
            pooled_ci_lower=ci_lower,
            pooled_ci_upper=ci_upper,
            tau_squared=tau_sq,
            q_statistic=q_stat,
            i_squared=i_sq,
            z_score=z_score,
            p_value=p_value,
            studies=studies,
            weights=weights_list,
        )

    @staticmethod
    def heterogeneity_summary(result: MetaAnalysisResult) -> Dict[str, str]:
        """Interpretação legível da heterogeneidade."""
        if result.i_squared < 25:
            level = "baixa"
        elif result.i_squared < 50:
            level = "moderada"
        elif result.i_squared < 75:
            level = "substancial"
        else:
            level = "considerável"

        return {
            "q_statistic": f"Q = {result.q_statistic:.2f} (df = {len(result.studies) - 1})",
            "i_squared": f"I² = {result.i_squared:.1f}% — heterogeneidade {level}",
            "tau_squared": f"τ² = {result.tau_squared:.4f}",
        }
