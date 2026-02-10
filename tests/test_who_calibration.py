"""Testes para calibração de pesos via WHO mortality."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from darwin_heliobiology.pipelines.who_calibration import (
    CalibratedWeights,
    PanelRegressionResult,
    WHOCalibrationConfig,
    calibrated_weights_from_json,
    calibrated_weights_to_json,
    derive_weights_from_betas,
    run_panel_regression,
)


def _make_panel(n_countries: int = 5, n_years: int = 10) -> pd.DataFrame:
    """Cria painel sintético (país × ano)."""
    rng = np.random.default_rng(42)
    rows = []
    for c in range(n_countries):
        for y in range(2010, 2010 + n_years):
            kp = rng.uniform(0.1, 0.6)
            dst = rng.uniform(0.05, 0.4)
            bz = rng.uniform(0.02, 0.3)
            sw = rng.uniform(0.01, 0.2)
            var = rng.uniform(0.01, 0.15)
            # Mortalidade correlacionada com Kp e Dst (efeito simulado)
            rate = 5.0 + 2.0 * kp + 1.5 * dst + rng.normal(0, 0.5)
            rows.append(
                {
                    "country": f"C{c:03d}",
                    "year": y,
                    "mortality_rate": rate,
                    "kp_activity": kp,
                    "dst_storm_intensity": dst,
                    "bz_reconnection": bz,
                    "solar_wind_pressure": sw,
                    "variability": var,
                }
            )
    return pd.DataFrame(rows)


def test_panel_regression_coefficients() -> None:
    """Regressão deve encontrar coeficientes para componentes solares."""
    panel = _make_panel(n_countries=10, n_years=15)
    config = WHOCalibrationConfig(outcome="suicide")
    result = run_panel_regression(panel, config)
    assert result.n_country_years > 0
    assert len(result.coefficients) > 0
    # Kp deve ter coeficiente positivo (dado efeito simulado)
    assert result.coefficients.get("kp_activity", 0) > 0


def test_panel_regression_empty_panel() -> None:
    """Painel vazio deve retornar resultado com coeficientes vazios."""
    config = WHOCalibrationConfig(outcome="test")
    result = run_panel_regression(pd.DataFrame(), config)
    assert result.n_country_years == 0
    assert result.coefficients == {}


def test_weights_sum_to_one() -> None:
    """Pesos calibrados devem somar 1.0."""
    results = [
        PanelRegressionResult(
            outcome="suicide",
            n_country_years=100,
            coefficients={
                "kp_activity": 0.5,
                "dst_storm_intensity": 0.3,
                "bz_reconnection": 0.1,
                "solar_wind_pressure": 0.08,
                "variability": 0.02,
            },
            std_errors={},
            p_values={},
            r_squared=0.3,
        ),
    ]
    calibrated = derive_weights_from_betas(results)
    assert abs(sum(calibrated.weights.values()) - 1.0) < 1e-10


def test_weights_floor() -> None:
    """Cada peso deve ser >= floor."""
    results = [
        PanelRegressionResult(
            outcome="test",
            n_country_years=100,
            coefficients={
                "kp_activity": 10.0,
                "dst_storm_intensity": 0.001,
                "bz_reconnection": 0.001,
                "solar_wind_pressure": 0.001,
                "variability": 0.001,
            },
            std_errors={},
            p_values={},
            r_squared=0.2,
        ),
    ]
    calibrated = derive_weights_from_betas(results, floor=0.05)
    for w in calibrated.weights.values():
        assert w >= 0.05


def test_json_roundtrip(tmp_path: Path) -> None:
    """JSON serialização deve ser reversível."""
    original = CalibratedWeights(
        weights={"kp_activity": 0.35, "dst_storm_intensity": 0.25},
        source="test",
        evidence_grade="C",
        regression_results=[
            PanelRegressionResult(
                outcome="suicide",
                n_country_years=50,
                coefficients={"kp_activity": 0.4},
                std_errors={"kp_activity": 0.1},
                p_values={"kp_activity": 0.001},
                r_squared=0.25,
            ),
        ],
    )
    json_path = tmp_path / "weights.json"
    calibrated_weights_to_json(original, json_path)
    loaded = calibrated_weights_from_json(json_path)
    assert loaded.weights == original.weights
    assert loaded.source == original.source
    assert loaded.evidence_grade == original.evidence_grade
    assert len(loaded.regression_results) == 1


def test_always_grade_c() -> None:
    """Pesos WHO devem sempre ser grau C (ecológico)."""
    results = [
        PanelRegressionResult(
            outcome="test",
            n_country_years=100,
            coefficients={"kp_activity": 0.3, "dst_storm_intensity": 0.2},
            std_errors={},
            p_values={},
            r_squared=0.5,
        ),
    ]
    calibrated = derive_weights_from_betas(results)
    assert calibrated.evidence_grade == "C"
