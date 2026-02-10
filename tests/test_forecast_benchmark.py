"""Testes para o benchmark de modelos de previsão."""

from __future__ import annotations

import numpy as np
import pandas as pd

from darwin_heliobiology.pipelines.forecast_benchmark import (
    BenchmarkResult,
    _compute_metrics,
    benchmark_to_dataframe,
    compute_kairos_baseline,
    run_benchmark,
)


def _make_omni_df(n: int = 500) -> pd.DataFrame:
    """Cria DataFrame OMNI2 sintético para testes."""
    rng = np.random.default_rng(42)
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=n, freq="h"),
            "kp_index": rng.uniform(0, 50, n),  # Kp*10 convention
            "dst_nt": rng.uniform(-50, 10, n),
            "bz_gsm_nt": rng.uniform(-5, 5, n),
            "speed_kms": rng.uniform(300, 600, n),
        }
    )


def test_compute_metrics_finite() -> None:
    """Métricas devem ser finitas para dados válidos."""
    y_true = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    y_pred = np.array([1.1, 2.2, 2.8, 4.1, 5.3])
    metrics = _compute_metrics(y_true, y_pred)
    assert np.isfinite(metrics["mae"])
    assert np.isfinite(metrics["rmse"])
    assert metrics["mae"] > 0
    assert metrics["rmse"] >= metrics["mae"]


def test_compute_metrics_nan_handling() -> None:
    """Métricas devem ignorar NaN em inputs."""
    y_true = np.array([1.0, float("nan"), 3.0])
    y_pred = np.array([1.1, 2.0, 2.8])
    metrics = _compute_metrics(y_true, y_pred)
    assert np.isfinite(metrics["mae"])


def test_kairos_baseline_result_structure() -> None:
    """Kairos baseline deve retornar BenchmarkResult com métricas finitas."""
    omni_df = _make_omni_df(500)
    train_df = omni_df.iloc[:400]
    test_df = omni_df.iloc[400:]

    result = compute_kairos_baseline(train_df, test_df, horizon=24)

    assert isinstance(result, BenchmarkResult)
    assert result.model_name == "kairos_baseline"
    assert result.horizon == 24
    assert np.isfinite(result.mae)
    assert np.isfinite(result.rmse)
    assert result.training_time_seconds >= 0
    assert result.n_train == 400
    assert result.n_test == 100


def test_run_benchmark_kairos_only() -> None:
    """run_benchmark com só Kairos deve retornar 1 resultado."""
    omni_df = _make_omni_df(500)
    results = run_benchmark(omni_df, horizon=24, models=["kairos"])
    assert len(results) == 1
    assert results[0].model_name == "kairos_baseline"


def test_benchmark_to_dataframe_schema() -> None:
    """DataFrame deve ter colunas esperadas."""
    results = [
        BenchmarkResult(
            model_name="kairos_baseline",
            horizon=24,
            mae=0.5,
            rmse=0.7,
            mape=15.0,
            training_time_seconds=1.2,
            n_train=400,
            n_test=100,
        ),
        BenchmarkResult(
            model_name="tft",
            horizon=24,
            mae=0.4,
            rmse=0.6,
            mape=12.0,
            training_time_seconds=120.0,
            n_train=400,
            n_test=100,
        ),
    ]
    df = benchmark_to_dataframe(results)
    assert len(df) == 2
    expected_cols = {
        "model",
        "horizon",
        "mae",
        "rmse",
        "mape",
        "training_time_s",
        "n_train",
        "n_test",
    }
    assert expected_cols <= set(df.columns)
