"""Calibração empírica do HelioMind Index contra dados OMNI2.

Computa distribuições empíricas de variáveis solares, sugere divisores baseados em
percentis (p99), e avalia sensibilidade dos pesos.  Ver docs/SCIENTIFIC_FOUNDATIONS.md §5.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]

# ── Pesos e divisores padrão (espelham helio_index.py) ────────────────────────

DEFAULT_WEIGHTS: Tuple[float, ...] = (0.35, 0.25, 0.20, 0.15, 0.05)
DEFAULT_DIVISORS: Tuple[float, ...] = (9.0, 78.0, 8.7, 4_364_643.0, 1.57)

COMPONENT_NAMES: Tuple[str, ...] = (
    "kp_activity",
    "dst_storm_intensity",
    "bz_reconnection",
    "solar_wind_pressure",
    "variability",
)

# Variáveis OMNI2 → transformação para comparação com divisor
_VARIABLE_SPEC: List[Dict[str, Any]] = [
    {"variable": "kp_index", "component": "kp_activity", "divisor_idx": 0},
    {"variable": "dst_nt", "component": "dst_storm_intensity", "divisor_idx": 1},
    {"variable": "bz_gsm_nt", "component": "bz_reconnection", "divisor_idx": 2},
    {"variable": "pressure_rho_v2", "component": "solar_wind_pressure", "divisor_idx": 3},
    {"variable": "kp_variability_12h", "component": "variability", "divisor_idx": 4},
]


# ── Dataclasses ───────────────────────────────────────────────────────────────


@dataclass(slots=True)
class EmpiricalDistribution:
    """Distribuição empírica de uma variável solar transformada."""

    variable: str
    count: int
    mean: float
    std: float
    p50: float
    p90: float
    p95: float
    p99: float
    max_abs: float
    current_divisor: float
    suggested_divisor: float


@dataclass(slots=True)
class WeightSensitivity:
    """Sensibilidade do score HelioMind a perturbação de um peso."""

    component: str
    base_weight: float
    mean_score_delta: float
    max_score_delta: float
    variance_contribution: float


@dataclass(slots=True)
class CalibrationReport:
    """Resultado completo da calibração empírica."""

    distributions: List[EmpiricalDistribution]
    sensitivities: List[WeightSensitivity]
    old_score_stats: Dict[str, float]
    new_score_stats: Dict[str, float]
    old_classification_counts: Dict[str, int]
    new_classification_counts: Dict[str, int]
    n_records: int
    years: List[int]
    timestamp: datetime


# ── Funções auxiliares ────────────────────────────────────────────────────────


def _transform_omni_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica as transformações que espelham helio_index.py normalization.

    OMNI2 armazena Kp * 10 (0–90). Detectamos automaticamente: se max(kp) > 9,
    dividimos por 10 para obter a escala real 0–9 usada pelo helio_index.py.
    """
    out = pd.DataFrame()
    kp = df["kp_index"].copy()
    if kp.max() > 9.5:  # OMNI2 convention: Kp * 10
        kp = kp / 10.0
    out["kp_index"] = kp
    out["dst_nt"] = df["dst_nt"].clip(upper=0).abs()
    out["bz_gsm_nt"] = (-df["bz_gsm_nt"]).clip(lower=0)

    if "proton_density_pcm3" in df.columns and "speed_kms" in df.columns:
        out["pressure_rho_v2"] = df["proton_density_pcm3"] * df["speed_kms"] ** 2
    else:
        out["pressure_rho_v2"] = np.nan

    kp_roll = kp.rolling(window=12, min_periods=2).std()
    out["kp_variability_12h"] = kp_roll
    return out


def _classify(score: float) -> str:
    if score < 0.33:
        return "estavel"
    if score < 0.66:
        return "vigilancia"
    return "alerta"


def _score_stats(scores: FloatArray) -> Dict[str, float]:
    return {
        "mean": float(np.nanmean(scores)),
        "std": float(np.nanstd(scores)),
        "p50": float(np.nanpercentile(scores, 50)),
        "p90": float(np.nanpercentile(scores, 90)),
        "p95": float(np.nanpercentile(scores, 95)),
        "p99": float(np.nanpercentile(scores, 99)),
    }


def _classification_counts(scores: FloatArray) -> Dict[str, int]:
    counts: Dict[str, int] = {"estavel": 0, "vigilancia": 0, "alerta": 0}
    for s in scores:
        if not np.isnan(s):
            counts[_classify(float(s))] += 1
    return counts


# ── Funções principais ────────────────────────────────────────────────────────


def compute_empirical_distributions(
    omni_df: pd.DataFrame,
) -> List[EmpiricalDistribution]:
    """Computa distribuições empíricas para cada variável solar transformada."""
    transformed = _transform_omni_columns(omni_df)
    results: List[EmpiricalDistribution] = []

    var_names = ["kp_index", "dst_nt", "bz_gsm_nt", "pressure_rho_v2", "kp_variability_12h"]

    for i, var_name in enumerate(var_names):
        series = transformed[var_name].dropna()
        if series.empty:
            results.append(
                EmpiricalDistribution(
                    variable=var_name,
                    count=0,
                    mean=0.0,
                    std=0.0,
                    p50=0.0,
                    p90=0.0,
                    p95=0.0,
                    p99=0.0,
                    max_abs=0.0,
                    current_divisor=DEFAULT_DIVISORS[i],
                    suggested_divisor=DEFAULT_DIVISORS[i],
                )
            )
            continue

        vals = series.to_numpy(dtype=np.float64)
        p99_val = float(np.percentile(vals, 99))
        suggested = max(p99_val, 1.0)
        if i == 0:
            suggested = 9.0  # Kp: manter escala NOAA oficial

        results.append(
            EmpiricalDistribution(
                variable=var_name,
                count=len(vals),
                mean=float(np.mean(vals)),
                std=float(np.std(vals)),
                p50=float(np.percentile(vals, 50)),
                p90=float(np.percentile(vals, 90)),
                p95=float(np.percentile(vals, 95)),
                p99=p99_val,
                max_abs=float(np.max(np.abs(vals))),
                current_divisor=DEFAULT_DIVISORS[i],
                suggested_divisor=suggested,
            )
        )

    return results


def compute_heliomind_scores_from_omni(
    omni_df: pd.DataFrame,
    *,
    divisors: Optional[Tuple[float, ...]] = None,
    weights: Optional[Tuple[float, ...]] = None,
) -> pd.DataFrame:
    """Computa HelioMind scores vetorizados sobre DataFrame OMNI2.

    Replica a lógica de ``helio_index._normalize_*`` em modo batch para
    processamento eficiente de >50k registros.
    """
    div = divisors or DEFAULT_DIVISORS
    w = weights or DEFAULT_WEIGHTS
    transformed = _transform_omni_columns(omni_df)

    components = pd.DataFrame()
    components["kp_activity"] = (transformed["kp_index"] / div[0]).clip(0, 1)
    components["dst_storm_intensity"] = (transformed["dst_nt"] / div[1]).clip(0, 1)
    components["bz_reconnection"] = (transformed["bz_gsm_nt"] / div[2]).clip(0, 1)
    components["solar_wind_pressure"] = (transformed["pressure_rho_v2"] / div[3]).clip(0, 1)
    components["variability"] = (transformed["kp_variability_12h"] / div[4]).clip(0, 1)

    score = (
        w[0] * components["kp_activity"]
        + w[1] * components["dst_storm_intensity"]
        + w[2] * components["bz_reconnection"]
        + w[3] * components["solar_wind_pressure"]
        + w[4] * components["variability"]
    ).clip(0, 1)

    result = components.copy()
    result["score"] = score
    result["classification"] = score.apply(lambda s: _classify(float(s)) if not np.isnan(s) else "")
    if "timestamp" in omni_df.columns:
        result["timestamp"] = omni_df["timestamp"].values
    return result


def run_weight_sensitivity_analysis(
    omni_df: pd.DataFrame,
    *,
    base_weights: Optional[Tuple[float, ...]] = None,
    perturbation: float = 0.10,
    divisors: Optional[Tuple[float, ...]] = None,
) -> List[WeightSensitivity]:
    """Analisa sensibilidade do score a perturbações em cada peso."""
    w = list(base_weights or DEFAULT_WEIGHTS)
    div = divisors or DEFAULT_DIVISORS

    baseline_scores = compute_heliomind_scores_from_omni(omni_df, divisors=div, weights=tuple(w))[
        "score"
    ].to_numpy(dtype=np.float64)
    baseline_var = float(np.nanvar(baseline_scores))

    results: List[WeightSensitivity] = []
    for i, comp in enumerate(COMPONENT_NAMES):
        deltas: List[float] = []
        for direction in [perturbation, -perturbation]:
            perturbed = list(w)
            perturbed[i] += direction
            # Renormalizar para somar 1
            total = sum(perturbed)
            if total > 0:
                perturbed = [p / total for p in perturbed]
            perturbed_scores = compute_heliomind_scores_from_omni(
                omni_df, divisors=div, weights=tuple(perturbed)
            )["score"].to_numpy(dtype=np.float64)
            diff = np.abs(perturbed_scores - baseline_scores)
            deltas.append(float(np.nanmean(diff)))
            deltas.append(float(np.nanmax(diff)))

        mean_delta = float(np.mean(deltas[:2]))
        max_delta = float(np.max(deltas))

        # Variância da componente isolada
        comp_scores = compute_heliomind_scores_from_omni(omni_df, divisors=div, weights=tuple(w))
        comp_vals = comp_scores[comp].to_numpy(dtype=np.float64)
        var_contrib = float(w[i] ** 2 * np.nanvar(comp_vals))
        frac = var_contrib / baseline_var if baseline_var > 0 else 0.0

        results.append(
            WeightSensitivity(
                component=comp,
                base_weight=w[i],
                mean_score_delta=mean_delta,
                max_score_delta=max_delta,
                variance_contribution=frac,
            )
        )

    return results


def build_calibration_report(omni_df: pd.DataFrame) -> CalibrationReport:
    """Orquestra calibração completa: distribuições + scores + sensibilidade."""
    distributions = compute_empirical_distributions(omni_df)

    # Scores com divisores antigos
    old_scores_df = compute_heliomind_scores_from_omni(omni_df, divisors=DEFAULT_DIVISORS)
    old_arr = old_scores_df["score"].to_numpy(dtype=np.float64)

    # Scores com divisores calibrados (p99)
    new_divs = tuple(d.suggested_divisor for d in distributions)
    new_scores_df = compute_heliomind_scores_from_omni(omni_df, divisors=new_divs)
    new_arr = new_scores_df["score"].to_numpy(dtype=np.float64)

    # Sensibilidade com divisores novos
    sensitivities = run_weight_sensitivity_analysis(omni_df, divisors=new_divs)

    years = sorted(
        int(y) for y in pd.to_datetime(omni_df["timestamp"]).dt.year.unique() if not np.isnan(y)
    )

    return CalibrationReport(
        distributions=distributions,
        sensitivities=sensitivities,
        old_score_stats=_score_stats(old_arr),
        new_score_stats=_score_stats(new_arr),
        old_classification_counts=_classification_counts(old_arr),
        new_classification_counts=_classification_counts(new_arr),
        n_records=len(omni_df),
        years=years,
        timestamp=datetime.now(tz=timezone.utc),
    )


def calibration_report_to_dataframe(report: CalibrationReport) -> pd.DataFrame:
    """Converte relatório em DataFrame para persistência."""
    rows: List[Dict[str, Any]] = []
    for d in report.distributions:
        rows.append(
            {
                "type": "distribution",
                "name": d.variable,
                "count": d.count,
                "mean": d.mean,
                "std": d.std,
                "p50": d.p50,
                "p90": d.p90,
                "p95": d.p95,
                "p99": d.p99,
                "max_abs": d.max_abs,
                "current_divisor": d.current_divisor,
                "suggested_divisor": d.suggested_divisor,
            }
        )
    for s in report.sensitivities:
        rows.append(
            {
                "type": "sensitivity",
                "name": s.component,
                "base_weight": s.base_weight,
                "mean_score_delta": s.mean_score_delta,
                "max_score_delta": s.max_score_delta,
                "variance_contribution": s.variance_contribution,
            }
        )
    return pd.DataFrame(rows)


def print_calibration_summary(report: CalibrationReport) -> None:
    """Imprime resumo legível da calibração."""
    print(f"\n{'=' * 60}")
    print("HelioMind Calibration Report")
    print(f"{'=' * 60}")
    print(f"Dados: OMNI2 {report.years[0]}-{report.years[-1]} | {report.n_records} registros")
    print()

    print("--- Distribuições Empíricas ---")
    print(f"{'Variável':<22} {'Atual':>8} {'Sugerido (p99)':>14} {'p50':>8} {'p90':>8} {'p99':>8}")
    for d in report.distributions:
        change = "" if d.current_divisor == d.suggested_divisor else " *"
        print(
            f"{d.variable:<22} {d.current_divisor:>8.1f} {d.suggested_divisor:>14.1f}{change}"
            f" {d.p50:>8.1f} {d.p90:>8.1f} {d.p99:>8.1f}"
        )

    print()
    print("--- Distribuição de Scores ---")
    print(f"{'':>22} {'OLD':>12} {'NEW (p99)':>12}")
    for key in ["mean", "std", "p50", "p90", "p99"]:
        print(
            f"{key:>22} {report.old_score_stats[key]:>12.4f}"
            f" {report.new_score_stats[key]:>12.4f}"
        )

    print()
    for label in ["estavel", "vigilancia", "alerta"]:
        old = report.old_classification_counts.get(label, 0)
        new = report.new_classification_counts.get(label, 0)
        total = max(report.n_records, 1)
        print(
            f"  {label:<12} {old:>6} ({old / total * 100:.1f}%) → {new:>6} ({new / total * 100:.1f}%)"
        )

    print()
    print("--- Sensibilidade dos Pesos ---")
    print(f"{'Componente':<22} {'Peso':>6} {'Mean Δ':>8} {'Var %':>8}")
    total_var = sum(s.variance_contribution for s in report.sensitivities)
    for s in report.sensitivities:
        pct = s.variance_contribution / total_var * 100 if total_var > 0 else 0
        print(f"{s.component:<22} {s.base_weight:>6.2f} {s.mean_score_delta:>8.4f} {pct:>7.1f}%")

    print()
    print("Recomendações:")
    for d in report.distributions:
        if d.current_divisor != d.suggested_divisor:
            print(f"  • {d.variable}: {d.current_divisor:.1f} → {d.suggested_divisor:.1f}")
    print(f"{'=' * 60}\n")


def prepare_solar_only_dataframe(
    omni_df: pd.DataFrame,
    *,
    solar_cols: Optional[List[str]] = None,
) -> Tuple[FloatArray, List[str]]:
    """Prepara array (T × N) de variáveis solares para PCMCI+.

    Retorna array numérico e lista de nomes curtos para exibição.
    """
    cols = solar_cols or ["kp_index", "dst_nt", "bz_gsm_nt", "speed_kms"]
    df = omni_df[["timestamp"] + [c for c in cols if c in omni_df.columns]].copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    # OMNI2 Kp*10 → Kp real
    if "kp_index" in df.columns and df["kp_index"].max() > 9.5:
        df["kp_index"] = df["kp_index"] / 10.0
    df = df.set_index("timestamp").resample("h").mean().dropna()

    short_names = [
        c.replace("_index", "").replace("_nt", "").replace("_gsm", "").replace("_kms", "")
        for c in cols
        if c in omni_df.columns
    ]
    return df.values.astype(np.float64), short_names
