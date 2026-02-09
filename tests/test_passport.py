"""Testes para o passaporte psico-geomagnético."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from darwin_heliobiology.services.passport import (
    PsychoGeomagneticPassport,
    SensitivityProfile,
    calibrate_passport,
    load_passport,
    passport_risk_adjustment,
    passport_to_dataframe,
)


def _make_aligned_data(
    n: int = 500,
    inject_lag: int = 0,
    inject_corr: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Gera DataFrames sintéticos alinhados (HRV+mood e solar).

    Se ``inject_corr`` é True, RMSSD é inversamente correlacionado com Kp
    deslocado por ``inject_lag`` horas.
    """
    rng = np.random.default_rng(42)
    timestamps = pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC")

    kp = rng.uniform(0, 9, n)
    dst = rng.uniform(-200, 20, n)
    bz = rng.uniform(-15, 15, n)

    if inject_corr and inject_lag < n - 10:
        # RMSSD inversamente correlacionado com Kp deslocado
        kp_shifted = np.roll(kp, inject_lag)
        rmssd = 60.0 - 3.0 * kp_shifted + rng.normal(0, 2, n)
    else:
        rmssd = rng.uniform(20, 80, n)

    sdnn = rng.uniform(30, 100, n)
    mood = rng.uniform(0.2, 0.9, n)
    hr = rng.uniform(55, 95, n)

    # Durante tempestades (Kp >= 5), mood cai
    storm_mask = kp >= 5.0
    mood[storm_mask] *= 0.6

    hrv_df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "hrv_rmssd": rmssd,
            "hrv_sdnn": sdnn,
            "mood_score": mood,
            "hr_mean": hr,
        }
    )
    solar_df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "kp_index": kp,
            "dst_nt": dst,
            "bz_gsm_nt": bz,
        }
    )
    return hrv_df, solar_df


def test_calibrate_passport_returns_valid_passport() -> None:
    hrv_df, solar_df = _make_aligned_data()
    passport = calibrate_passport("test_subject", hrv_df, solar_df)

    assert isinstance(passport, PsychoGeomagneticPassport)
    assert passport.subject_id == "test_subject"
    assert passport.n_observations > 0
    assert 0.0 <= passport.sensitivity.composite_sensitivity <= 1.0


def test_baseline_computation() -> None:
    hrv_df, solar_df = _make_aligned_data(n=200)
    passport = calibrate_passport("baselines", hrv_df, solar_df)

    # Baselines devem estar nas faixas razoáveis dos dados sintéticos
    assert 10.0 < passport.baseline_rmssd < 90.0
    assert 20.0 < passport.baseline_sdnn < 110.0
    assert 0.0 < passport.baseline_mood < 1.0
    assert 40.0 < passport.baseline_hr < 110.0


def test_optimal_lag_detection() -> None:
    """Injeta correlação com lag=12 e verifica se a detecção encontra ~12."""
    hrv_df, solar_df = _make_aligned_data(n=500, inject_lag=12, inject_corr=True)
    passport = calibrate_passport("lag_test", hrv_df, solar_df, lag_max=48)

    # O lag ótimo deve estar próximo de 12 (±5h de tolerância)
    assert abs(passport.sensitivity.optimal_lag_hours - 12) <= 5


def test_kp_coefficient_sign() -> None:
    """RMSSD inversamente correlacionado com Kp → coeficiente negativo."""
    hrv_df, solar_df = _make_aligned_data(n=500, inject_lag=0, inject_corr=True)
    passport = calibrate_passport("sign_test", hrv_df, solar_df)

    # Kp↑ → RMSSD↓, então o coeficiente deve ser negativo
    assert passport.sensitivity.kp_coefficient < 0


def test_storm_impact_score() -> None:
    """Com mood reduzido durante tempestades, storm_impact_score deve ser positivo."""
    hrv_df, solar_df = _make_aligned_data(n=500)
    passport = calibrate_passport("storm_test", hrv_df, solar_df)

    assert passport.storm_impact_score > 0.0
    assert passport.storm_impact_score <= 1.0


def test_passport_to_dataframe_roundtrip(tmp_path: Path) -> None:
    hrv_df, solar_df = _make_aligned_data(n=200)
    passport = calibrate_passport("roundtrip", hrv_df, solar_df)

    df = passport_to_dataframe(passport)
    assert len(df) == 1
    assert "subject_id" in df.columns
    assert "kp_coefficient" in df.columns
    assert "composite_sensitivity" in df.columns
    assert "vulnerable_periods" in df.columns

    # Persistir e recarregar
    out_path = tmp_path / "test_passport.parquet"
    df.to_parquet(out_path)

    loaded = load_passport(out_path)
    assert loaded.subject_id == "roundtrip"
    assert loaded.sensitivity.kp_coefficient == pytest.approx(
        passport.sensitivity.kp_coefficient, abs=1e-4
    )
    assert loaded.sensitivity.composite_sensitivity == pytest.approx(
        passport.sensitivity.composite_sensitivity, abs=1e-4
    )


def test_passport_risk_adjustment_range() -> None:
    sensitivity = SensitivityProfile(
        kp_coefficient=-0.4,
        dst_coefficient=0.3,
        bz_coefficient=-0.2,
        optimal_lag_hours=12,
        composite_sensitivity=0.6,
    )
    passport = PsychoGeomagneticPassport(
        subject_id="risk_test",
        created_at=pd.Timestamp("2024-01-01", tz="UTC").to_pydatetime(),
        baseline_rmssd=50.0,
        baseline_sdnn=60.0,
        baseline_mood=0.5,
        baseline_hr=70.0,
        sensitivity=sensitivity,
        vulnerable_periods=[],
        storm_impact_score=0.3,
        training_start=pd.Timestamp("2024-01-01", tz="UTC").to_pydatetime(),
        training_end=pd.Timestamp("2024-06-01", tz="UTC").to_pydatetime(),
        n_observations=1000,
    )

    # Condições calmas → risco baixo
    calm_risk = passport_risk_adjustment(passport, kp=1.0, dst=-10.0)
    assert 0.0 <= calm_risk <= 1.0

    # Tempestade → risco mais alto
    storm_risk = passport_risk_adjustment(passport, kp=8.0, dst=-150.0)
    assert 0.0 <= storm_risk <= 1.0
    assert storm_risk > calm_risk


def test_calibrate_passport_no_overlap_raises() -> None:
    """DataFrames sem overlap temporal devem levantar ValueError."""
    hrv_df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2020-01-01", periods=10, freq="h"),
            "hrv_rmssd": [50.0] * 10,
            "hrv_sdnn": [60.0] * 10,
            "mood_score": [0.5] * 10,
            "hr_mean": [70.0] * 10,
        }
    )
    solar_df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=10, freq="h"),
            "kp_index": [3.0] * 10,
            "dst_nt": [-20.0] * 10,
            "bz_gsm_nt": [-1.0] * 10,
        }
    )
    with pytest.raises(ValueError, match="Nenhuma observação alinhada"):
        calibrate_passport("no_overlap", hrv_df, solar_df)
