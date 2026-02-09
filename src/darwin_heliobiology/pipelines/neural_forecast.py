"""Pipeline de previsão com TFT e PatchTST via NeuralForecast.

Consome features do HelioMind Index e HRV como covariáveis exógenas para prever
atividade geomagnética (Kp, Dst) ou score composto HelioMind. Complementa o
``KairosForecaster`` baseline com modelos de deep learning.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

# Colunas exógenas padrão (covariáveis estáticas/históricas)
DEFAULT_SOLAR_EXOG = ["dst_nt", "bz_gsm_nt", "speed_kms"]
DEFAULT_HRV_EXOG = ["hrv_rmssd", "hrv_sdnn"]


@dataclass(slots=True)
class NeuralForecastConfig:
    """Configuração para treinamento TFT ou PatchTST."""

    model_type: str = "tft"
    horizon: int = 24
    input_size: int = 168
    max_steps: int = 500
    learning_rate: float = 1e-3
    batch_size: int = 32
    target_col: str = "kp_index"


@dataclass(slots=True)
class NeuralForecastResult:
    """Resultado de treinamento e previsão."""

    model_type: str
    predictions: pd.DataFrame
    metrics: Dict[str, float] = field(default_factory=dict)
    config: Optional[NeuralForecastConfig] = None


def prepare_neuralforecast_df(
    solar_df: pd.DataFrame,
    hrv_df: Optional[pd.DataFrame] = None,
    *,
    target_col: str = "kp_index",
    solar_exog: Optional[List[str]] = None,
    hrv_exog: Optional[List[str]] = None,
    unique_id: str = "helio",
) -> pd.DataFrame:
    """Prepara DataFrame no formato NeuralForecast (unique_id, ds, y + exógenas).

    Parameters
    ----------
    solar_df:
        DataFrame com coluna ``timestamp`` e variáveis solares.
    hrv_df:
        DataFrame opcional com coluna ``timestamp`` e HRV features.
    target_col:
        Coluna alvo para previsão (default: kp_index).
    solar_exog:
        Covariáveis solares exógenas além do alvo.
    hrv_exog:
        Covariáveis HRV exógenas.
    unique_id:
        Identificador da série temporal.

    Returns
    -------
    pd.DataFrame
        DataFrame com colunas ``unique_id``, ``ds``, ``y`` e exógenas.
    """
    solar_exog = solar_exog if solar_exog is not None else DEFAULT_SOLAR_EXOG
    hrv_exog = hrv_exog if hrv_exog is not None else DEFAULT_HRV_EXOG

    df = solar_df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp")

    # Merge HRV se disponível
    if hrv_df is not None:
        hrv = hrv_df.copy()
        hrv["timestamp"] = pd.to_datetime(hrv["timestamp"])
        df = pd.merge_asof(
            df.sort_values("timestamp"),
            hrv[["timestamp"] + [c for c in hrv_exog if c in hrv.columns]].sort_values("timestamp"),
            on="timestamp",
            direction="nearest",
        )

    # Montar formato NeuralForecast
    result = pd.DataFrame({"unique_id": unique_id, "ds": df["timestamp"], "y": df[target_col]})

    # Adicionar exógenas disponíveis
    for col in solar_exog:
        if col in df.columns and col != target_col:
            result[col] = df[col].values

    if hrv_df is not None:
        for col in hrv_exog:
            if col in df.columns:
                result[col] = df[col].values

    result = result.dropna(subset=["y"]).reset_index(drop=True)
    return result


def build_neural_forecaster(
    config: NeuralForecastConfig,
    exog_cols: Optional[List[str]] = None,
) -> Any:
    """Instancia NeuralForecast com TFT ou PatchTST.

    Parameters
    ----------
    config:
        Configuração do modelo.
    exog_cols:
        Lista de colunas exógenas disponíveis no DataFrame de treino.

    Returns
    -------
    NeuralForecast
        Instância configurada pronta para ``.fit()``.
    """
    try:
        from neuralforecast import NeuralForecast
        from neuralforecast.models import PatchTST, TFT
    except ImportError as exc:
        raise ImportError(
            "neuralforecast é necessário para o pipeline neural. "
            "Instale com: pip install neuralforecast"
        ) from exc

    hist_exog = exog_cols or []

    model_kwargs: Dict[str, Any] = {
        "h": config.horizon,
        "input_size": config.input_size,
        "max_steps": config.max_steps,
        "learning_rate": config.learning_rate,
        "batch_size": config.batch_size,
        "scaler_type": "standard",
    }

    if hist_exog:
        model_kwargs["hist_exog_list"] = hist_exog

    if config.model_type == "tft":
        model = TFT(**model_kwargs)
    elif config.model_type == "patchtst":
        model_kwargs.pop("hist_exog_list", None)
        model = PatchTST(**model_kwargs)
    else:
        raise ValueError(f"Modelo desconhecido: {config.model_type}. Use 'tft' ou 'patchtst'.")

    return NeuralForecast(models=[model], freq="h")


def train_and_forecast(
    df: pd.DataFrame,
    config: NeuralForecastConfig,
) -> NeuralForecastResult:
    """Treina modelo e gera previsão no horizonte configurado.

    Parameters
    ----------
    df:
        DataFrame no formato NeuralForecast (unique_id, ds, y + exógenas).
    config:
        Configuração do modelo.

    Returns
    -------
    NeuralForecastResult
    """
    reserved = {"unique_id", "ds", "y"}
    exog_cols = [c for c in df.columns if c not in reserved]

    # Split temporal 80/20
    n = len(df)
    split_idx = int(n * 0.8)
    train_df = df.iloc[:split_idx].copy()
    val_df = df.iloc[split_idx:].copy()

    nf = build_neural_forecaster(config, exog_cols=exog_cols if exog_cols else None)
    nf.fit(df=train_df)

    predictions = nf.predict()

    # Métricas no conjunto de validação
    metrics: Dict[str, float] = {}
    if not val_df.empty and not predictions.empty:
        y_true = val_df["y"].values[: config.horizon]
        model_col = [c for c in predictions.columns if c not in reserved][0]
        y_pred = predictions[model_col].values[: len(y_true)]

        if len(y_true) > 0 and len(y_pred) > 0:
            min_len = min(len(y_true), len(y_pred))
            y_true = y_true[:min_len]
            y_pred = y_pred[:min_len]

            metrics["mae"] = float(np.mean(np.abs(y_true - y_pred)))
            metrics["rmse"] = float(np.sqrt(np.mean(np.square(y_true - y_pred))))
            mask = np.abs(y_true) > 1e-8
            if mask.any():
                metrics["mape"] = float(
                    np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100
                )

    return NeuralForecastResult(
        model_type=config.model_type,
        predictions=predictions,
        metrics=metrics,
        config=config,
    )


def compare_with_kairos(
    neural_result: NeuralForecastResult,
    kairos_metrics: Dict[str, float],
) -> Dict[str, Any]:
    """Comparação lado a lado entre neural forecast e baseline Kairos.

    Parameters
    ----------
    neural_result:
        Resultado do pipeline neural.
    kairos_metrics:
        Métricas do KairosForecaster (dicionário com mae, rmse, etc.).

    Returns
    -------
    Dict com comparações por métrica.
    """
    comparison: Dict[str, Any] = {
        "model": neural_result.model_type,
        "neural_metrics": neural_result.metrics,
        "kairos_metrics": kairos_metrics,
        "improvements": {},
    }

    for metric in ["mae", "rmse", "mape"]:
        neural_val = neural_result.metrics.get(metric)
        kairos_val = kairos_metrics.get(metric)
        if neural_val is not None and kairos_val is not None and kairos_val > 0:
            improvement = (kairos_val - neural_val) / kairos_val * 100
            comparison["improvements"][metric] = round(improvement, 2)

    return comparison
