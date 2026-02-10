"""Testes para os componentes do dashboard."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from darwin_heliobiology.dashboard.components import (
    build_forecast_comparison,
    build_helio_mind_timeseries,
    build_kp_timeseries,
    build_meta_forest_plot,
)


def test_build_kp_timeseries_returns_figure() -> None:
    """Testa se build_kp_timeseries retorna um go.Figure válido."""
    df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2025-01-01", periods=24, freq="h"),
            "kp_index": [
                2.0,
                2.3,
                2.7,
                3.0,
                3.5,
                4.0,
                5.0,
                6.0,
                7.0,
                6.5,
                5.5,
                4.5,
                3.5,
                3.0,
                2.5,
                2.0,
                1.5,
                2.0,
                2.5,
                3.0,
                3.5,
                4.0,
                4.5,
                5.0,
            ],
        }
    )

    fig = build_kp_timeseries(df)

    assert isinstance(fig, go.Figure)
    assert len(fig.data) >= 1
    assert fig.layout.title.text == "Índice Kp (Planetary K-index)"


def test_build_helio_mind_timeseries_returns_figure() -> None:
    """Testa se build_helio_mind_timeseries retorna um go.Figure válido."""
    df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2025-01-01", periods=24, freq="h"),
            "helio_mind_score": [
                0.2,
                0.25,
                0.3,
                0.4,
                0.5,
                0.6,
                0.7,
                0.75,
                0.8,
                0.7,
                0.6,
                0.5,
                0.4,
                0.35,
                0.3,
                0.25,
                0.2,
                0.25,
                0.3,
                0.35,
                0.4,
                0.45,
                0.5,
                0.55,
            ],
        }
    )

    fig = build_helio_mind_timeseries(df)

    assert isinstance(fig, go.Figure)
    assert len(fig.data) >= 1
    assert fig.layout.title.text == "HelioMind Index"


def test_build_forecast_comparison_returns_figure() -> None:
    """Testa se build_forecast_comparison retorna um go.Figure válido."""
    index = pd.date_range("2025-01-01", periods=24, freq="h")
    actual = pd.Series(
        [
            2.0,
            2.5,
            3.0,
            3.5,
            4.0,
            5.0,
            6.0,
            7.0,
            6.5,
            5.5,
            4.5,
            3.5,
            3.0,
            2.5,
            2.0,
            2.5,
            3.0,
            3.5,
            4.0,
            4.5,
            5.0,
            5.5,
            6.0,
            6.5,
        ],
        index=index,
    )
    kairos_pred = pd.Series(
        [
            2.1,
            2.4,
            3.1,
            3.4,
            4.1,
            4.9,
            6.1,
            6.9,
            6.6,
            5.4,
            4.6,
            3.4,
            3.1,
            2.6,
            2.1,
            2.4,
            3.1,
            3.4,
            4.1,
            4.4,
            5.1,
            5.4,
            6.1,
            6.4,
        ],
        index=index,
    )

    fig = build_forecast_comparison(actual, kairos_pred, kairos_pred)

    assert isinstance(fig, go.Figure)
    assert len(fig.data) >= 2
    assert fig.layout.title.text == "Comparação de Previsões"


def test_build_forecast_comparison_with_neural() -> None:
    """Testa se build_forecast_comparison funciona com previsão neural separada."""
    index = pd.date_range("2025-01-01", periods=24, freq="h")
    actual = pd.Series(
        [
            2.0,
            2.5,
            3.0,
            3.5,
            4.0,
            5.0,
            6.0,
            7.0,
            6.5,
            5.5,
            4.5,
            3.5,
            3.0,
            2.5,
            2.0,
            2.5,
            3.0,
            3.5,
            4.0,
            4.5,
            5.0,
            5.5,
            6.0,
            6.5,
        ],
        index=index,
    )
    kairos_pred = pd.Series(
        [
            2.1,
            2.4,
            3.1,
            3.4,
            4.1,
            4.9,
            6.1,
            6.9,
            6.6,
            5.4,
            4.6,
            3.4,
            3.1,
            2.6,
            2.1,
            2.4,
            3.1,
            3.4,
            4.1,
            4.4,
            5.1,
            5.4,
            6.1,
            6.4,
        ],
        index=index,
    )
    neural_pred = pd.Series(
        [
            2.0,
            2.5,
            3.0,
            3.6,
            4.0,
            5.1,
            5.9,
            7.1,
            6.4,
            5.6,
            4.4,
            3.6,
            2.9,
            2.4,
            2.1,
            2.6,
            3.1,
            3.6,
            4.0,
            4.6,
            5.0,
            5.6,
            5.9,
            6.6,
        ],
        index=index,
    )

    fig = build_forecast_comparison(actual, kairos_pred, neural_pred)

    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 3  # actual, kairos, neural


def test_build_meta_forest_plot_returns_figure() -> None:
    """Testa se build_meta_forest_plot retorna um go.Figure válido."""
    effect_sizes = [1.15, 1.08, 1.22, 1.05, 1.12]
    cis = [(1.05, 1.26), (0.98, 1.19), (1.10, 1.35), (0.97, 1.14), (1.02, 1.23)]
    labels = ["Estudo A", "Estudo B", "Estudo C", "Estudo D", "Estudo E"]

    fig = build_meta_forest_plot(effect_sizes, cis, labels)

    assert isinstance(fig, go.Figure)
    assert len(fig.data) > 0
    assert fig.layout.title.text == "Forest Plot - Meta-Análise"
