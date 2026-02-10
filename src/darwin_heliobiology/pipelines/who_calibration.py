"""Calibração de pesos do HelioMind Index via regressão sobre mortalidade WHO.

Usa dados anuais de mortalidade (país × ano) alinhados com médias anuais de
atividade solar (OMNI2) para estimar pesos via regressão OLS com efeitos fixos
de país e ano.

**Grau C** — dados ecológicos, resolução anual, controle incompleto de
confundidores (latitude, PIB, acesso a saúde).  Melhoria sobre Grau D (arbitrário).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd


@dataclass(slots=True)
class WHOCalibrationConfig:
    """Configuração para calibração de pesos via WHO."""

    outcome: str = "suicide"
    icd10_prefixes: List[str] = field(default_factory=lambda: [f"X{i}" for i in range(60, 85)])
    solar_components: List[str] = field(
        default_factory=lambda: [
            "kp_activity",
            "dst_storm_intensity",
            "bz_reconnection",
            "solar_wind_pressure",
            "variability",
        ]
    )
    min_year: int = 2000
    max_year: int = 2022


@dataclass(slots=True)
class PanelRegressionResult:
    """Resultado de regressão em painel (país × ano)."""

    outcome: str
    n_country_years: int
    coefficients: Dict[str, float]
    std_errors: Dict[str, float]
    p_values: Dict[str, float]
    r_squared: float
    evidence_grade: str = "C"


@dataclass(slots=True)
class CalibratedWeights:
    """Pesos calibrados para o HelioMind Index."""

    weights: Dict[str, float]
    source: str
    evidence_grade: str
    regression_results: List[PanelRegressionResult]


# ---------------------------------------------------------------------------
# Preparação de dados
# ---------------------------------------------------------------------------


def prepare_who_solar_panel(
    who_dir: Path,
    omni_df: pd.DataFrame,
    config: WHOCalibrationConfig,
) -> pd.DataFrame:
    """Alinha mortalidade WHO anual com médias anuais de atividade solar.

    Parameters
    ----------
    who_dir:
        Diretório com CSVs extraídos de ``fetch_who_mortality``.
    omni_df:
        DataFrame OMNI2 horário com coluna ``timestamp``.
    config:
        Configuração com filtros de ICD-10 e intervalo de anos.

    Returns
    -------
    pd.DataFrame
        Painel com colunas: country, year, mortality_rate,
        kp_activity, dst_storm_intensity, bz_reconnection,
        solar_wind_pressure, variability.
    """
    # --- Agregar solares por ano ---
    solar_annual = _aggregate_solar_annual(omni_df, config)

    # --- Carregar e agregar mortalidade ---
    mortality_annual = _load_mortality_annual(who_dir, config)

    if mortality_annual.empty:
        return pd.DataFrame()

    # --- Merge ---
    panel = mortality_annual.merge(solar_annual, on="year", how="inner")
    return panel


def _aggregate_solar_annual(
    omni_df: pd.DataFrame,
    config: WHOCalibrationConfig,
) -> pd.DataFrame:
    """Computa médias anuais das componentes solares."""
    df = omni_df.copy()
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df["year"] = df["timestamp"].dt.year
    elif "year" not in df.columns:
        raise ValueError("omni_df precisa de coluna 'timestamp' ou 'year'.")

    df = df[(df["year"] >= config.min_year) & (df["year"] <= config.max_year)]

    # Componentes normalizadas (0..1) — reusa lógica do helio_index
    kp = df["kp_index"].copy()
    if kp.max() > 9.5:
        kp = kp / 10.0
    df["kp_activity"] = kp / 9.0

    dst = df["dst_nt"].copy()
    df["dst_storm_intensity"] = np.clip(np.abs(np.minimum(dst, 0.0)) / 78.0, 0.0, 1.0)

    if "bz_gsm_nt" in df.columns:
        bz = df["bz_gsm_nt"].copy()
    else:
        bz = pd.Series(0.0, index=df.index)
    df["bz_reconnection"] = np.clip(np.maximum(-bz, 0.0) / 8.7, 0.0, 1.0)

    if "speed_kms" in df.columns and "proton_density_pcm3" in df.columns:
        pressure = df["proton_density_pcm3"] * df["speed_kms"] ** 2
        df["solar_wind_pressure"] = np.clip(pressure / 4_364_643.0, 0.0, 1.0)
    else:
        df["solar_wind_pressure"] = 0.0

    df["variability"] = 0.0  # Placeholder — std(Kp,12h) requer janela rolling

    agg_cols = config.solar_components
    annual = df.groupby("year")[agg_cols].mean().reset_index()
    return annual


def _load_mortality_annual(
    who_dir: Path,
    config: WHOCalibrationConfig,
) -> pd.DataFrame:
    """Carrega e agrega mortalidade WHO por país × ano."""
    who_dir = who_dir.expanduser().resolve()
    csv_files = sorted(who_dir.glob("Morticd10_part*.csv")) + sorted(
        who_dir.glob("morticd10_part*.csv")
    )

    if not csv_files:
        return pd.DataFrame()

    frames: List[pd.DataFrame] = []
    for csv_path in csv_files:
        df = pd.read_csv(csv_path, low_memory=False)
        cause_col = "Cause" if "Cause" in df.columns else "cause"
        year_col = "Year" if "Year" in df.columns else "year"
        country_col = "Country" if "Country" in df.columns else "country"

        # Filtrar por ICD-10 prefixes
        mask = df[cause_col].astype(str).str[:3].isin(config.icd10_prefixes)
        filtered = df[mask].copy()

        if filtered.empty:
            continue

        # Agregar mortes por país × ano
        # WHO usa colunas Deaths1..Deaths26 para faixas etárias; Deaths1 = total
        death_cols = [c for c in filtered.columns if c.startswith("Deaths")]
        if not death_cols:
            continue

        # Usar Deaths1 (total) se disponível, senão somar todas
        total_col = "Deaths1" if "Deaths1" in filtered.columns else death_cols[0]
        filtered["deaths"] = pd.to_numeric(filtered[total_col], errors="coerce").fillna(0)

        agg = (
            filtered.groupby([country_col, year_col])["deaths"]
            .sum()
            .reset_index()
            .rename(columns={country_col: "country", year_col: "year"})
        )
        frames.append(agg)

    if not frames:
        return pd.DataFrame()

    mortality = pd.concat(frames, ignore_index=True)
    mortality = mortality.groupby(["country", "year"])["deaths"].sum().reset_index()

    # Filtrar intervalo de anos
    mortality = mortality[
        (mortality["year"] >= config.min_year) & (mortality["year"] <= config.max_year)
    ]

    # Taxa simplificada: mortes per 100k (sem população = mortes brutas)
    # Com população real, dividir por pop × 100k
    pop_path = who_dir / "pop"
    if pop_path.exists():
        mortality = _join_population(mortality, pop_path)
    else:
        # Sem dados de população → usar contagem bruta
        mortality["mortality_rate"] = mortality["deaths"].astype(float)

    return mortality


def _join_population(mortality_df: pd.DataFrame, pop_dir: Path) -> pd.DataFrame:
    """Junta dados populacionais para calcular taxa per 100k."""
    pop_files = sorted(pop_dir.glob("*.csv")) + sorted(pop_dir.parent.glob("pop*.csv"))
    if not pop_files:
        mortality_df["mortality_rate"] = mortality_df["deaths"].astype(float)
        return mortality_df

    pop_df = pd.read_csv(pop_files[0], low_memory=False)
    country_col = "Country" if "Country" in pop_df.columns else "country"
    year_col = "Year" if "Year" in pop_df.columns else "year"
    pop_col = "Pop1" if "Pop1" in pop_df.columns else "pop"

    if pop_col not in pop_df.columns:
        mortality_df["mortality_rate"] = mortality_df["deaths"].astype(float)
        return mortality_df

    pop_agg = (
        pop_df.groupby([country_col, year_col])[pop_col]
        .sum()
        .reset_index()
        .rename(columns={country_col: "country", year_col: "year", pop_col: "population"})
    )
    pop_agg["population"] = pd.to_numeric(pop_agg["population"], errors="coerce")

    merged = mortality_df.merge(pop_agg, on=["country", "year"], how="left")
    merged["mortality_rate"] = np.where(
        merged["population"] > 0,
        merged["deaths"] / merged["population"] * 100_000,
        merged["deaths"].astype(float),
    )
    return merged


# ---------------------------------------------------------------------------
# Regressão em painel
# ---------------------------------------------------------------------------


def run_panel_regression(
    panel_df: pd.DataFrame,
    config: WHOCalibrationConfig,
) -> PanelRegressionResult:
    """OLS com efeitos fixos de país e ano.

    Modelo: mortality_rate ~ β₁·kp_activity + β₂·dst_storm_intensity + ... + FE_country + FE_year
    """
    if panel_df.empty or len(panel_df) < 10:
        return PanelRegressionResult(
            outcome=config.outcome,
            n_country_years=len(panel_df),
            coefficients={},
            std_errors={},
            p_values={},
            r_squared=0.0,
        )

    df = panel_df.copy()
    y = np.asarray(df["mortality_rate"].values, dtype=np.float64)

    # Variáveis solares
    solar_cols = [c for c in config.solar_components if c in df.columns]
    if not solar_cols:
        return PanelRegressionResult(
            outcome=config.outcome,
            n_country_years=len(df),
            coefficients={},
            std_errors={},
            p_values={},
            r_squared=0.0,
        )

    X_solar = np.asarray(df[solar_cols].values, dtype=np.float64)

    # Efeitos fixos via dummies (demeaning é mais eficiente mas dummies são claras)
    if "country" in df.columns:
        country_dummies = pd.get_dummies(df["country"], prefix="fe_c", drop_first=True)
    else:
        country_dummies = pd.DataFrame(index=df.index)

    if "year" in df.columns:
        year_dummies = pd.get_dummies(df["year"], prefix="fe_y", drop_first=True)
    else:
        year_dummies = pd.DataFrame(index=df.index)

    X_fe = np.asarray(pd.concat([country_dummies, year_dummies], axis=1).values, dtype=np.float64)
    X = np.column_stack([X_solar, X_fe, np.ones(len(y))])  # intercepto

    # Remover NaN
    mask = ~(np.isnan(y) | np.isnan(X).any(axis=1))
    X = X[mask]
    y = y[mask]

    if len(y) < X.shape[1] + 1:
        return PanelRegressionResult(
            outcome=config.outcome,
            n_country_years=len(y),
            coefficients={},
            std_errors={},
            p_values={},
            r_squared=0.0,
        )

    # OLS via normal equations
    try:
        beta, residuals, rank, sv = np.linalg.lstsq(X, y, rcond=None)
    except np.linalg.LinAlgError:
        return PanelRegressionResult(
            outcome=config.outcome,
            n_country_years=len(y),
            coefficients={},
            std_errors={},
            p_values={},
            r_squared=0.0,
        )

    y_hat = X @ beta
    ss_res = float(np.sum((y - y_hat) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r_sq = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

    # Standard errors
    n_obs, k = X.shape
    dof = max(n_obs - k, 1)
    mse = ss_res / dof
    try:
        var_beta = mse * np.diag(np.linalg.inv(X.T @ X))
        se = np.sqrt(np.maximum(var_beta, 0.0))
    except np.linalg.LinAlgError:
        se = np.full(k, float("nan"))

    # p-values via t-distribution (scipy-free approximation: normal)
    t_stats = beta / np.where(se > 1e-15, se, 1.0)
    # Rough 2-sided p: erfc(|t|/sqrt(2)) — good enough for grade C
    from math import erfc, sqrt

    p_vals = np.array([erfc(abs(float(t)) / sqrt(2)) for t in t_stats])

    coefficients = {col: float(beta[i]) for i, col in enumerate(solar_cols)}
    std_errs = {col: float(se[i]) for i, col in enumerate(solar_cols)}
    p_values = {col: float(p_vals[i]) for i, col in enumerate(solar_cols)}

    return PanelRegressionResult(
        outcome=config.outcome,
        n_country_years=int(len(y)),
        coefficients=coefficients,
        std_errors=std_errs,
        p_values=p_values,
        r_squared=float(r_sq),
    )


# ---------------------------------------------------------------------------
# Derivação de pesos
# ---------------------------------------------------------------------------


def derive_weights_from_betas(
    results: List[PanelRegressionResult],
    *,
    floor: float = 0.05,
) -> CalibratedWeights:
    """Converte |β_standardized| em pesos normalizados (soma = 1).

    Parameters
    ----------
    results:
        Lista de resultados de regressão (um por outcome).
    floor:
        Peso mínimo para cada componente.
    """
    # Agregar coeficientes absolutos
    component_sums: Dict[str, float] = {}
    for r in results:
        for comp, coeff in r.coefficients.items():
            component_sums[comp] = component_sums.get(comp, 0.0) + abs(coeff)

    if not component_sums:
        # Fallback: pesos uniformes
        default_comps = [
            "kp_activity",
            "dst_storm_intensity",
            "bz_reconnection",
            "solar_wind_pressure",
            "variability",
        ]
        weights = {c: 1.0 / len(default_comps) for c in default_comps}
        return CalibratedWeights(
            weights=weights,
            source="fallback_uniform",
            evidence_grade="D",
            regression_results=results,
        )

    # Normalizar com floor
    total = sum(component_sums.values())
    if total < 1e-15:
        n = len(component_sums)
        weights = {c: 1.0 / n for c in component_sums}
    else:
        raw = {c: v / total for c, v in component_sums.items()}
        # Aplicar floor: componentes abaixo do floor ficam fixos,
        # o orçamento restante é distribuído proporcionalmente.
        floored_comps = {c for c, v in raw.items() if v < floor}
        budget = 1.0 - floor * len(floored_comps)
        free_total = sum(v for c, v in raw.items() if c not in floored_comps)
        weights = {}
        for c, v in raw.items():
            if c in floored_comps:
                weights[c] = floor
            elif free_total > 1e-15:
                weights[c] = v / free_total * budget
            else:
                weights[c] = budget / max(len(raw) - len(floored_comps), 1)

    return CalibratedWeights(
        weights=weights,
        source="who_panel_regression",
        evidence_grade="C",
        regression_results=results,
    )


# ---------------------------------------------------------------------------
# Persistência
# ---------------------------------------------------------------------------


def calibrated_weights_to_json(
    calibrated: CalibratedWeights,
    output_path: Path,
) -> None:
    """Persiste pesos calibrados em JSON."""
    output_path = output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data: Dict[str, Any] = {
        "weights": calibrated.weights,
        "source": calibrated.source,
        "evidence_grade": calibrated.evidence_grade,
        "regressions": [
            {
                "outcome": r.outcome,
                "n_country_years": r.n_country_years,
                "coefficients": r.coefficients,
                "std_errors": r.std_errors,
                "p_values": r.p_values,
                "r_squared": r.r_squared,
                "evidence_grade": r.evidence_grade,
            }
            for r in calibrated.regression_results
        ],
    }
    output_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def calibrated_weights_from_json(json_path: Path) -> CalibratedWeights:
    """Carrega pesos calibrados de JSON."""
    data = json.loads(json_path.read_text(encoding="utf-8"))
    regressions = [
        PanelRegressionResult(
            outcome=r["outcome"],
            n_country_years=r["n_country_years"],
            coefficients=r["coefficients"],
            std_errors=r["std_errors"],
            p_values=r["p_values"],
            r_squared=r["r_squared"],
            evidence_grade=r.get("evidence_grade", "C"),
        )
        for r in data.get("regressions", [])
    ]
    return CalibratedWeights(
        weights=data["weights"],
        source=data["source"],
        evidence_grade=data["evidence_grade"],
        regression_results=regressions,
    )
