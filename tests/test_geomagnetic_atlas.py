"""Testes para o atlas temporal de assinaturas geomagnéticas."""

import pandas as pd
import pytest

from darwin_heliobiology.core.geomagnetic_atlas import (
    AtlasResult,
    GeomagneticSignature,
    atlas_to_dataframe,
    build_geomagnetic_atlas,
)


def _make_omni_df(days: int = 60) -> pd.DataFrame:
    """DataFrame sintético com formato OMNI2 para 'days' dias de dados horários."""
    timestamps = pd.date_range("2024-01-01", periods=days * 24, freq="h", tz="UTC")
    rng = pd.np if hasattr(pd, "np") else __import__("numpy")
    n = len(timestamps)
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "kp_index": rng.random.default_rng(42).uniform(0, 9, n),
            "dst_nt": rng.random.default_rng(43).uniform(-200, 20, n),
            "bz_gsm_nt": rng.random.default_rng(44).uniform(-15, 15, n),
        }
    )


def test_build_monthly_atlas() -> None:
    df = _make_omni_df(days=60)
    result = build_geomagnetic_atlas(df, resolution="monthly")

    assert isinstance(result, AtlasResult)
    assert result.resolution == "monthly"
    assert len(result.signatures) >= 2  # janeiro + fevereiro
    assert result.year_range == (2024, 2024)

    for sig in result.signatures:
        assert isinstance(sig, GeomagneticSignature)
        assert 0 <= sig.bz_southward_fraction <= 1.0


def test_build_daily_atlas() -> None:
    df = _make_omni_df(days=3)
    result = build_geomagnetic_atlas(df, resolution="daily")

    assert len(result.signatures) >= 3
    for sig in result.signatures:
        assert sig.period_label.startswith("2024-01-")


def test_build_quarterly_atlas() -> None:
    df = _make_omni_df(days=120)
    result = build_geomagnetic_atlas(df, resolution="quarterly")

    assert len(result.signatures) >= 1
    assert "Q" in result.signatures[0].period_label


def test_storm_hours_reflects_kp() -> None:
    """Kp todos >= 5 → storm_hours == total de registros no período."""
    timestamps = pd.date_range("2024-03-01", periods=24, freq="h", tz="UTC")
    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "kp_index": [6.0] * 24,
            "dst_nt": [-50.0] * 24,
            "bz_gsm_nt": [-5.0] * 24,
        }
    )
    result = build_geomagnetic_atlas(df, resolution="daily")
    assert result.signatures[0].storm_hours == 24


def test_atlas_to_dataframe() -> None:
    df = _make_omni_df(days=30)
    result = build_geomagnetic_atlas(df, resolution="monthly")
    out_df = atlas_to_dataframe(result)

    assert "period_label" in out_df.columns
    assert "storm_hours" in out_df.columns
    assert len(out_df) == len(result.signatures)


def test_invalid_resolution_raises() -> None:
    df = _make_omni_df(days=10)
    with pytest.raises(ValueError, match="Resolução inválida"):
        build_geomagnetic_atlas(df, resolution="weekly")


def test_missing_columns_raises() -> None:
    df = pd.DataFrame({"timestamp": [1, 2], "kp_index": [3.0, 4.0]})
    with pytest.raises(ValueError, match="Colunas ausentes"):
        build_geomagnetic_atlas(df, resolution="daily")


def test_absent_values_stay_nan_and_storm_hours_bounded_by_valid_hours() -> None:
    import numpy as np

    idx = pd.date_range("2024-01-01", periods=24, freq="h", tz="UTC")
    kp = [6.0] * 6 + [np.nan] * 18
    df = pd.DataFrame(
        {"timestamp": idx, "kp_index": kp, "dst_nt": [np.nan] * 24, "bz_gsm_nt": [np.nan] * 24}
    )
    sig = build_geomagnetic_atlas(df, "daily").signatures[0]
    assert sig.storm_hours == 6 and sig.valid_hours == 6
    assert sig.storm_hours <= sig.valid_hours
    assert np.isnan(sig.mean_dst) and np.isnan(sig.min_dst) and np.isnan(sig.mean_bz)
    assert np.isnan(sig.bz_southward_fraction)


def test_legacy_kp_times_ten_is_rescaled_before_counting_storms() -> None:
    idx = pd.date_range("2024-01-01", periods=24, freq="h", tz="UTC")
    kp10 = [30.0] * 20 + [60.0] * 4  # Kp 3.0 e 6.0 na escala ×10
    df = pd.DataFrame(
        {"timestamp": idx, "kp_index": kp10, "dst_nt": [0.0] * 24, "bz_gsm_nt": [0.0] * 24}
    )
    assert build_geomagnetic_atlas(df, "daily").signatures[0].storm_hours == 4
