"""Testes para o pipeline TFT/PatchTST de previsão neural."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from darwin_heliobiology.pipelines.neural_forecast import (
    NeuralForecastConfig,
    NeuralForecastResult,
    compare_with_kairos,
    prepare_neuralforecast_df,
)


def _make_solar_df(n: int = 200) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    timestamps = pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC")
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "kp_index": rng.uniform(0, 9, n),
            "dst_nt": rng.uniform(-200, 20, n),
            "bz_gsm_nt": rng.uniform(-15, 15, n),
            "speed_kms": rng.uniform(300, 700, n),
        }
    )


def _make_hrv_df(n: int = 200) -> pd.DataFrame:
    rng = np.random.default_rng(43)
    timestamps = pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC")
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "hrv_rmssd": rng.uniform(20, 80, n),
            "hrv_sdnn": rng.uniform(30, 100, n),
        }
    )


def test_prepare_neuralforecast_df_solar_only() -> None:
    solar = _make_solar_df()
    df = prepare_neuralforecast_df(solar)

    assert "unique_id" in df.columns
    assert "ds" in df.columns
    assert "y" in df.columns
    assert len(df) > 0
    # Exógenas solares disponíveis
    assert "dst_nt" in df.columns


def test_prepare_neuralforecast_df_with_hrv() -> None:
    solar = _make_solar_df()
    hrv = _make_hrv_df()
    df = prepare_neuralforecast_df(solar, hrv)

    assert "unique_id" in df.columns
    assert "y" in df.columns
    assert "hrv_rmssd" in df.columns


def test_prepare_neuralforecast_df_custom_target() -> None:
    solar = _make_solar_df()
    df = prepare_neuralforecast_df(solar, target_col="dst_nt")

    assert df["y"].iloc[0] == solar["dst_nt"].iloc[0]


def test_prepare_neuralforecast_df_no_nan_in_y() -> None:
    solar = _make_solar_df()
    solar.loc[0, "kp_index"] = np.nan
    df = prepare_neuralforecast_df(solar)

    assert not df["y"].isna().any()


def test_build_neural_forecaster_with_mock() -> None:
    """Verifica que build_neural_forecaster instancia NeuralForecast corretamente."""
    import sys
    from unittest.mock import MagicMock, patch

    mock_tft_cls = MagicMock()
    mock_patchtst_cls = MagicMock()
    mock_nf_cls = MagicMock()

    mock_models_mod = MagicMock()
    mock_models_mod.TFT = mock_tft_cls
    mock_models_mod.PatchTST = mock_patchtst_cls

    mock_nf_mod = MagicMock()
    mock_nf_mod.NeuralForecast = mock_nf_cls

    neuralforecast_mocks = {
        "neuralforecast": mock_nf_mod,
        "neuralforecast.models": mock_models_mod,
    }

    from darwin_heliobiology.pipelines.neural_forecast import build_neural_forecaster

    config = NeuralForecastConfig(model_type="tft", horizon=12, input_size=48, max_steps=100)

    with patch.dict(sys.modules, neuralforecast_mocks):
        build_neural_forecaster(config, exog_cols=["dst_nt"])

    mock_tft_cls.assert_called_once()
    mock_nf_cls.assert_called_once()


def test_train_and_forecast_with_mock() -> None:
    """Testa train_and_forecast com NeuralForecast mockado."""
    import sys

    solar = _make_solar_df(300)
    df = prepare_neuralforecast_df(solar)

    config = NeuralForecastConfig(model_type="tft", horizon=24, input_size=48, max_steps=10)

    # Previsões mockadas
    mock_predictions = pd.DataFrame(
        {
            "unique_id": ["helio"] * 24,
            "ds": pd.date_range("2024-01-13 08:00", periods=24, freq="h"),
            "TFT": np.random.default_rng(42).uniform(2, 6, 24),
        }
    )

    mock_nf_instance = MagicMock()
    mock_nf_instance.fit.return_value = None
    mock_nf_instance.predict.return_value = mock_predictions

    mock_tft_cls = MagicMock()
    mock_nf_cls = MagicMock(return_value=mock_nf_instance)

    mock_models_mod = MagicMock()
    mock_models_mod.TFT = mock_tft_cls
    mock_models_mod.PatchTST = MagicMock()

    mock_nf_mod = MagicMock()
    mock_nf_mod.NeuralForecast = mock_nf_cls

    neuralforecast_mocks = {
        "neuralforecast": mock_nf_mod,
        "neuralforecast.models": mock_models_mod,
    }

    from darwin_heliobiology.pipelines.neural_forecast import train_and_forecast

    with patch.dict(sys.modules, neuralforecast_mocks):
        result = train_and_forecast(df, config)

    assert isinstance(result, NeuralForecastResult)
    assert result.model_type == "tft"
    assert not result.predictions.empty


def test_compare_with_kairos() -> None:
    neural = NeuralForecastResult(
        model_type="tft",
        predictions=pd.DataFrame(),
        metrics={"mae": 1.5, "rmse": 2.0},
    )
    kairos_metrics = {"mae": 2.5, "rmse": 3.0}

    comparison = compare_with_kairos(neural, kairos_metrics)

    assert comparison["model"] == "tft"
    assert "mae" in comparison["improvements"]
    assert comparison["improvements"]["mae"] == pytest.approx(40.0)
    assert comparison["improvements"]["rmse"] == pytest.approx(33.33, abs=0.01)
