"""Passaporte psico-geomagnético: perfil individual de sensibilidade.

Calibra parâmetros personalizados de resposta geomagnética a partir de dados
longitudinais HRV+mood+solar, substituindo a heurística pontual de
``AutonomicSnapshot.normalized_sensitivity()`` por coeficientes aprendidos
via correlação cruzada.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class SensitivityProfile:
    """Coeficientes de resposta individual por variável solar."""

    kp_coefficient: float
    dst_coefficient: float
    bz_coefficient: float
    optimal_lag_hours: int
    composite_sensitivity: float


@dataclass(slots=True)
class PsychoGeomagneticPassport:
    """Passaporte psico-geomagnético individual."""

    subject_id: str
    created_at: datetime

    # Baselines pessoais
    baseline_rmssd: float
    baseline_sdnn: float
    baseline_mood: float
    baseline_hr: float

    # Sensibilidade aprendida
    sensitivity: SensitivityProfile

    # Períodos vulneráveis (labels do atlas geomagnético)
    vulnerable_periods: List[str]
    storm_impact_score: float

    # Proveniência
    training_start: datetime
    training_end: datetime
    n_observations: int
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Calibração
# ---------------------------------------------------------------------------

# Mapeamento coluna solar → nome curto
_SOLAR_COL_MAP: Dict[str, str] = {
    "kp_index": "kp",
    "dst_nt": "dst",
    "bz_gsm_nt": "bz",
}

# Pesos para composite sensitivity (somam 1.0)
_COEF_WEIGHTS: Dict[str, float] = {"kp": 0.50, "dst": 0.30, "bz": 0.20}


def _cross_correlate_at_lags(
    solar_series: np.ndarray,
    bio_series: np.ndarray,
    max_lag: int,
) -> Tuple[int, float]:
    """Retorna (melhor_lag, coeficiente) via correlação de Pearson em cada lag.

    ``solar_series`` é deslocado para trás (solar precede bio).
    """
    best_lag = 0
    best_abs_r = 0.0
    best_r = 0.0

    n = len(solar_series)
    for lag in range(0, min(max_lag + 1, n - 10)):
        solar_shifted = solar_series[: n - lag] if lag > 0 else solar_series
        bio_aligned = bio_series[lag:] if lag > 0 else bio_series

        min_len = min(len(solar_shifted), len(bio_aligned))
        if min_len < 10:
            continue

        s = solar_shifted[:min_len]
        b = bio_aligned[:min_len]

        # Ignorar se variância é zero
        if np.std(s) < 1e-12 or np.std(b) < 1e-12:
            continue

        r, _ = scipy_stats.pearsonr(s, b)
        if abs(r) > best_abs_r:
            best_abs_r = abs(r)
            best_r = float(r)
            best_lag = lag

    return best_lag, best_r


def _compute_storm_impact(
    merged: pd.DataFrame,
    kp_col: str = "kp_index",
    mood_col: str = "mood_score",
    storm_threshold: float = 5.0,
) -> float:
    """Calcula impacto de tempestades sobre o humor (desvio normalizado 0..1)."""
    calm = merged.loc[merged[kp_col] < storm_threshold, mood_col]
    storm = merged.loc[merged[kp_col] >= storm_threshold, mood_col]

    if calm.empty or storm.empty:
        return 0.0

    calm_mean = float(calm.mean())
    storm_mean = float(storm.mean())

    if calm_mean < 1e-8:
        return 0.0

    # Desvio relativo: quanto o mood cai durante tempestades
    deviation = (calm_mean - storm_mean) / calm_mean
    return float(np.clip(deviation, 0.0, 1.0))


def _identify_vulnerable_periods(
    merged: pd.DataFrame,
    mood_col: str = "mood_score",
    kp_col: str = "kp_index",
) -> List[str]:
    """Identifica meses onde o humor desvia mais que 1 desvio-padrão abaixo da média pessoal."""
    if "timestamp" not in merged.columns:
        return []

    merged = merged.copy()
    merged["month_label"] = (
        pd.to_datetime(merged["timestamp"]).dt.tz_localize(None).dt.to_period("M").astype(str)
    )

    global_mean = merged[mood_col].mean()
    global_std = merged[mood_col].std()
    if global_std < 1e-8:
        return []

    threshold = global_mean - global_std

    monthly = merged.groupby("month_label").agg(
        mean_mood=(mood_col, "mean"),
        mean_kp=(kp_col, "mean"),
    )

    vulnerable = monthly[monthly["mean_mood"] < threshold].index.tolist()
    return sorted(vulnerable)


def calibrate_passport(
    subject_id: str,
    hrv_mood_df: pd.DataFrame,
    solar_df: pd.DataFrame,
    *,
    lag_max: int = 72,
    hrv_col: str = "hrv_rmssd",
    sdnn_col: str = "hrv_sdnn",
    mood_col: str = "mood_score",
    hr_col: str = "hr_mean",
    solar_cols: Optional[List[str]] = None,
) -> PsychoGeomagneticPassport:
    """Calibra passaporte psico-geomagnético a partir de dados longitudinais.

    Parameters
    ----------
    subject_id:
        Identificador do sujeito.
    hrv_mood_df:
        DataFrame com colunas ``timestamp``, ``hrv_rmssd``, ``hrv_sdnn``,
        ``mood_score``, ``hr_mean``.
    solar_df:
        DataFrame com colunas ``timestamp``, ``kp_index``, ``dst_nt``, ``bz_gsm_nt``.
    lag_max:
        Lag máximo em horas para correlação cruzada.

    Returns
    -------
    PsychoGeomagneticPassport
    """
    solar_cols = solar_cols or list(_SOLAR_COL_MAP.keys())

    # --- Preparar e alinhar ---
    bio = hrv_mood_df[["timestamp", hrv_col, sdnn_col, mood_col, hr_col]].copy()
    bio["timestamp"] = pd.to_datetime(bio["timestamp"])
    bio = bio.set_index("timestamp").resample("h").mean().dropna()

    sol = solar_df[["timestamp"] + solar_cols].copy()
    sol["timestamp"] = pd.to_datetime(sol["timestamp"])
    sol = sol.set_index("timestamp").resample("h").mean().dropna()

    merged = bio.join(sol, how="inner")
    if merged.empty:
        raise ValueError("Nenhuma observação alinhada entre HRV e dados solares.")

    merged = merged.reset_index()
    n_obs = len(merged)

    # --- Baselines ---
    baseline_rmssd = float(merged[hrv_col].mean())
    baseline_sdnn = float(merged[sdnn_col].mean())
    baseline_mood = float(merged[mood_col].mean())
    baseline_hr = float(merged[hr_col].mean())

    # --- Correlação cruzada por variável solar ---
    bio_array = np.asarray(merged[hrv_col], dtype=np.float64)
    coefficients: Dict[str, float] = {}
    lags: Dict[str, int] = {}

    for solar_col in solar_cols:
        short = _SOLAR_COL_MAP.get(solar_col, solar_col)
        solar_array = np.asarray(merged[solar_col], dtype=np.float64)
        lag, r = _cross_correlate_at_lags(solar_array, bio_array, max_lag=lag_max)
        coefficients[short] = r
        lags[short] = lag

    # Melhor lag global (o da variável com maior |r|)
    best_var = max(coefficients, key=lambda k: abs(coefficients[k]))
    optimal_lag = lags[best_var]

    # Composite sensitivity: média ponderada dos |coeficientes|
    composite = sum(_COEF_WEIGHTS.get(k, 0.0) * abs(v) for k, v in coefficients.items())
    composite = float(np.clip(composite, 0.0, 1.0))

    sensitivity = SensitivityProfile(
        kp_coefficient=coefficients.get("kp", 0.0),
        dst_coefficient=coefficients.get("dst", 0.0),
        bz_coefficient=coefficients.get("bz", 0.0),
        optimal_lag_hours=optimal_lag,
        composite_sensitivity=composite,
    )

    # --- Storm impact ---
    storm_impact = _compute_storm_impact(merged, kp_col="kp_index", mood_col=mood_col)

    # --- Períodos vulneráveis ---
    vulnerable = _identify_vulnerable_periods(merged, mood_col=mood_col, kp_col="kp_index")

    # --- Timestamps de proveniência ---
    ts = merged["timestamp"]
    training_start = ts.min().to_pydatetime()
    training_end = ts.max().to_pydatetime()

    return PsychoGeomagneticPassport(
        subject_id=subject_id,
        created_at=datetime.now(tz=timezone.utc),
        baseline_rmssd=baseline_rmssd,
        baseline_sdnn=baseline_sdnn,
        baseline_mood=baseline_mood,
        baseline_hr=baseline_hr,
        sensitivity=sensitivity,
        vulnerable_periods=vulnerable,
        storm_impact_score=storm_impact,
        training_start=training_start,
        training_end=training_end,
        n_observations=n_obs,
        metadata={
            "lag_max": lag_max,
            "coefficients": coefficients,
            "lags": lags,
        },
    )


# ---------------------------------------------------------------------------
# Persistência e carregamento
# ---------------------------------------------------------------------------


def passport_to_dataframe(passport: PsychoGeomagneticPassport) -> pd.DataFrame:
    """Converte passaporte em DataFrame de uma linha para persistência."""
    row = {
        "subject_id": passport.subject_id,
        "created_at": passport.created_at,
        "baseline_rmssd": passport.baseline_rmssd,
        "baseline_sdnn": passport.baseline_sdnn,
        "baseline_mood": passport.baseline_mood,
        "baseline_hr": passport.baseline_hr,
        "kp_coefficient": passport.sensitivity.kp_coefficient,
        "dst_coefficient": passport.sensitivity.dst_coefficient,
        "bz_coefficient": passport.sensitivity.bz_coefficient,
        "optimal_lag_hours": passport.sensitivity.optimal_lag_hours,
        "composite_sensitivity": passport.sensitivity.composite_sensitivity,
        "vulnerable_periods": json.dumps(passport.vulnerable_periods),
        "storm_impact_score": passport.storm_impact_score,
        "training_start": passport.training_start,
        "training_end": passport.training_end,
        "n_observations": passport.n_observations,
    }
    return pd.DataFrame([row])


def load_passport(path: Path) -> PsychoGeomagneticPassport:
    """Reconstrói passaporte a partir de arquivo Parquet ou CSV."""
    p = path.expanduser().resolve()
    if p.suffix == ".parquet":
        df = pd.read_parquet(p)
    elif p.suffix == ".csv":
        df = pd.read_csv(p)
    else:
        raise ValueError(f"Formato não suportado: {p.suffix}")

    row = df.iloc[0]

    vulnerable = json.loads(str(row["vulnerable_periods"])) if row["vulnerable_periods"] else []

    sensitivity = SensitivityProfile(
        kp_coefficient=float(row["kp_coefficient"]),
        dst_coefficient=float(row["dst_coefficient"]),
        bz_coefficient=float(row["bz_coefficient"]),
        optimal_lag_hours=int(row["optimal_lag_hours"]),
        composite_sensitivity=float(row["composite_sensitivity"]),
    )

    return PsychoGeomagneticPassport(
        subject_id=str(row["subject_id"]),
        created_at=pd.Timestamp(row["created_at"]).to_pydatetime(),
        baseline_rmssd=float(row["baseline_rmssd"]),
        baseline_sdnn=float(row["baseline_sdnn"]),
        baseline_mood=float(row["baseline_mood"]),
        baseline_hr=float(row["baseline_hr"]),
        sensitivity=sensitivity,
        vulnerable_periods=vulnerable,
        storm_impact_score=float(row["storm_impact_score"]),
        training_start=pd.Timestamp(row["training_start"]).to_pydatetime(),
        training_end=pd.Timestamp(row["training_end"]).to_pydatetime(),
        n_observations=int(row["n_observations"]),
    )


# ---------------------------------------------------------------------------
# Ajuste de risco personalizado
# ---------------------------------------------------------------------------


def passport_risk_adjustment(
    passport: PsychoGeomagneticPassport,
    kp: float,
    dst: float,
) -> float:
    """Multiplier de risco informado pelo passaporte (substitui normalized_sensitivity).

    Usa coeficientes aprendidos em vez da heurística RMSSD/SDNN pontual.
    Retorna valor em [0, 1].
    """
    s = passport.sensitivity

    kp_risk = abs(s.kp_coefficient) * float(np.clip((kp - 3.0) / 6.0, 0.0, 1.0))
    dst_risk = abs(s.dst_coefficient) * float(np.clip((-dst - 20.0) / 130.0, 0.0, 1.0))

    combined = 0.6 * kp_risk + 0.4 * dst_risk
    base = 0.3 + 0.7 * s.composite_sensitivity

    return float(np.clip(combined * base, 0.0, 1.0))
