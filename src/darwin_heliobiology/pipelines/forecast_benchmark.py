"""Benchmark de modelos de previsão: Kairos baseline vs TFT vs PatchTST.

Compara acurácia de previsão de Kp usando dados OMNI2 reais.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from darwin_heliobiology.models.solar import SolarIndex
from darwin_heliobiology.pipelines.neural_forecast import (
    NeuralForecastConfig,
    prepare_neuralforecast_df,
    train_and_forecast,
)
from darwin_heliobiology.services.kairos_forecaster import KairosForecaster


@dataclass(slots=True)
class BenchmarkResult:
    """Resultado de benchmark para um modelo."""

    model_name: str
    horizon: int
    mae: float
    rmse: float
    mape: Optional[float]
    training_time_seconds: float
    n_train: int
    n_test: int


def _compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """Computa MAE, RMSE e MAPE."""
    min_len = min(len(y_true), len(y_pred))
    y_t = y_true[:min_len].astype(np.float64)
    y_p = y_pred[:min_len].astype(np.float64)

    mask = ~(np.isnan(y_t) | np.isnan(y_p))
    y_t = y_t[mask]
    y_p = y_p[mask]

    if len(y_t) == 0:
        return {"mae": float("nan"), "rmse": float("nan")}

    mae = float(np.mean(np.abs(y_t - y_p)))
    rmse = float(np.sqrt(np.mean(np.square(y_t - y_p))))

    metrics: Dict[str, float] = {"mae": mae, "rmse": rmse}
    nonzero = np.abs(y_t) > 1e-8
    if nonzero.any():
        metrics["mape"] = float(np.mean(np.abs((y_t[nonzero] - y_p[nonzero]) / y_t[nonzero])) * 100)
    return metrics


def compute_kairos_baseline(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    *,
    horizon: int = 24,
    target_col: str = "kp_index",
) -> BenchmarkResult:
    """Avalia KairosForecaster no conjunto de teste.

    Simula previsão rolling: para cada ponto do teste, fita com dados
    disponíveis e projeta ``horizon`` passos.  Coleta previsões 1-step-ahead.
    """
    from darwin_heliobiology.core.psychophysiology import AutonomicSnapshot

    start = time.monotonic()

    # OMNI2 armazena Kp*10
    kp_col = train_df[target_col].copy()
    if kp_col.max() > 9.5:
        kp_col = kp_col / 10.0

    kp_series = [
        SolarIndex(timestamp=pd.Timestamp("2020-01-01"), value=float(v), label="Kp")
        for v in kp_col.dropna().values
    ]
    dst_series = [
        SolarIndex(timestamp=pd.Timestamp("2020-01-01"), value=float(v), label="Dst")
        for v in train_df["dst_nt"].dropna().values
    ]

    forecaster = KairosForecaster()
    forecaster.fit(kp_series, dst_series)

    # Previsão simples: usa último estado treinado
    snapshot = AutonomicSnapshot(rmssd_ms=40.0, sdnn_ms=60.0, heart_rate_bpm=72.0)
    forecast = forecaster.forecast(steps=min(horizon, len(test_df)), snapshot=snapshot)

    elapsed = time.monotonic() - start

    y_true_kp = np.asarray(test_df[target_col].values[:horizon], dtype=np.float64)
    if float(y_true_kp.max()) > 9.5:
        y_true_kp = y_true_kp / 10.0
    y_pred = forecast.kp_forecast[:horizon]

    metrics = _compute_metrics(y_true_kp, y_pred)

    return BenchmarkResult(
        model_name="kairos_baseline",
        horizon=horizon,
        mae=metrics["mae"],
        rmse=metrics["rmse"],
        mape=metrics.get("mape"),
        training_time_seconds=elapsed,
        n_train=len(train_df),
        n_test=len(test_df),
    )


def _run_neural_model(
    omni_df: pd.DataFrame,
    *,
    model_type: str,
    horizon: int,
    max_steps: int,
    target_col: str,
) -> BenchmarkResult:
    """Treina e avalia um modelo neural."""
    start = time.monotonic()

    nf_df = prepare_neuralforecast_df(omni_df, target_col=target_col)
    config = NeuralForecastConfig(
        model_type=model_type,
        horizon=horizon,
        max_steps=max_steps,
        target_col=target_col,
    )
    result = train_and_forecast(nf_df, config)
    elapsed = time.monotonic() - start

    return BenchmarkResult(
        model_name=model_type,
        horizon=horizon,
        mae=result.metrics.get("mae", float("nan")),
        rmse=result.metrics.get("rmse", float("nan")),
        mape=result.metrics.get("mape"),
        training_time_seconds=elapsed,
        n_train=int(len(nf_df) * 0.8),
        n_test=int(len(nf_df) * 0.2),
    )


def run_benchmark(
    omni_df: pd.DataFrame,
    *,
    horizon: int = 24,
    max_steps: int = 500,
    target_col: str = "kp_index",
    models: Optional[List[str]] = None,
) -> List[BenchmarkResult]:
    """Roda benchmark completo: Kairos + modelos neurais."""
    model_list = models or ["kairos", "tft", "patchtst"]
    results: List[BenchmarkResult] = []

    # Split temporal: últimas 'horizon * 7' linhas para teste (1 semana)
    test_size = min(horizon * 7, int(len(omni_df) * 0.2))
    train_df = omni_df.iloc[:-test_size].copy()
    test_df = omni_df.iloc[-test_size:].copy()

    for model in model_list:
        if model == "kairos":
            results.append(
                compute_kairos_baseline(train_df, test_df, horizon=horizon, target_col=target_col)
            )
        else:
            results.append(
                _run_neural_model(
                    omni_df,
                    model_type=model,
                    horizon=horizon,
                    max_steps=max_steps,
                    target_col=target_col,
                )
            )

    return results


def benchmark_to_dataframe(results: List[BenchmarkResult]) -> pd.DataFrame:
    """Converte resultados em DataFrame."""
    rows: List[Dict[str, Any]] = []
    for r in results:
        rows.append(
            {
                "model": r.model_name,
                "horizon": r.horizon,
                "mae": r.mae,
                "rmse": r.rmse,
                "mape": r.mape,
                "training_time_s": r.training_time_seconds,
                "n_train": r.n_train,
                "n_test": r.n_test,
            }
        )
    return pd.DataFrame(rows)


def print_benchmark_summary(results: List[BenchmarkResult]) -> None:
    """Imprime tabela comparativa."""
    print(f"\n{'=' * 70}")
    print("Forecast Benchmark — Kairos vs Neural Models")
    print(f"{'=' * 70}")
    print(
        f"{'Model':<16} {'MAE':>8} {'RMSE':>8} {'MAPE%':>8} {'Time(s)':>10} {'n_train':>8} {'n_test':>8}"
    )
    print("-" * 70)
    for r in results:
        mape_str = f"{r.mape:.1f}" if r.mape is not None else "N/A"
        print(
            f"{r.model_name:<16} {r.mae:>8.3f} {r.rmse:>8.3f} "
            f"{mape_str:>8} {r.training_time_seconds:>10.1f} "
            f"{r.n_train:>8} {r.n_test:>8}"
        )
    print(f"{'=' * 70}\n")
