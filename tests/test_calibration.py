"""Testes para o módulo de calibração empírica do HelioMind Index."""

from __future__ import annotations

import numpy as np
import pandas as pd

from darwin_heliobiology.pipelines.calibration import (
    CalibrationReport,
    EmpiricalDistribution,
    build_calibration_report,
    calibration_report_to_dataframe,
    compute_empirical_distributions,
    compute_heliomind_scores_from_omni,
    prepare_solar_only_dataframe,
    run_weight_sensitivity_analysis,
)


def _make_synthetic_omni(n: int = 500, seed: int = 42) -> pd.DataFrame:
    """Gera DataFrame OMNI2-like com distribuições realistas."""
    rng = np.random.default_rng(seed)
    timestamps = pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC")
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "kp_index": rng.exponential(1.5, n).clip(0, 9),
            "dst_nt": rng.normal(-10, 30, n).clip(-300, 50),
            "bz_gsm_nt": rng.normal(0, 4, n).clip(-25, 25),
            "speed_kms": rng.normal(400, 80, n).clip(250, 900),
            "proton_density_pcm3": rng.exponential(5, n).clip(0.1, 100),
        }
    )


def test_compute_empirical_distributions_basic():
    df = _make_synthetic_omni()
    dists = compute_empirical_distributions(df)

    assert len(dists) == 5
    for d in dists:
        assert isinstance(d, EmpiricalDistribution)
        assert d.count > 0
        assert d.p50 <= d.p90 <= d.p95 <= d.p99
        assert d.suggested_divisor > 0


def test_compute_empirical_distributions_handles_nan():
    df = _make_synthetic_omni(n=200)
    df.loc[0:50, "dst_nt"] = np.nan
    df.loc[0:30, "bz_gsm_nt"] = np.nan

    dists = compute_empirical_distributions(df)
    dst_dist = next(d for d in dists if d.variable == "dst_nt")
    bz_dist = next(d for d in dists if d.variable == "bz_gsm_nt")

    assert dst_dist.count < 200
    assert bz_dist.count < 200
    assert dst_dist.count > 0
    assert bz_dist.count > 0


def test_heliomind_scores_bounds():
    df = _make_synthetic_omni()
    result = compute_heliomind_scores_from_omni(df)

    scores = result["score"].dropna()
    assert (scores >= 0).all()
    assert (scores <= 1).all()
    valid_classes = set(result["classification"].unique()) - {""}
    assert valid_classes <= {"estavel", "vigilancia", "alerta"}


def test_heliomind_scores_custom_divisors():
    df = _make_synthetic_omni()

    default_scores = compute_heliomind_scores_from_omni(df)["score"].dropna()
    # Divisores menores → scores maiores
    smaller_divs = (9.0, 150.0, 10.0, 150_000.0, 1.25)
    higher_scores = compute_heliomind_scores_from_omni(df, divisors=smaller_divs)["score"].dropna()

    assert higher_scores.mean() > default_scores.mean()


def test_weight_sensitivity_kp_dominates():
    df = _make_synthetic_omni(n=300)
    sensitivities = run_weight_sensitivity_analysis(df)

    assert len(sensitivities) == 5
    kp_sens = next(s for s in sensitivities if s.component == "kp_activity")
    var_sens = next(s for s in sensitivities if s.component == "variability")

    # Kp (peso 0.35) deve ter contribuição de variância maior que variabilidade (peso 0.05)
    assert kp_sens.variance_contribution > var_sens.variance_contribution


def test_build_calibration_report_full():
    df = _make_synthetic_omni()
    report = build_calibration_report(df)

    assert isinstance(report, CalibrationReport)
    assert len(report.distributions) == 5
    assert len(report.sensitivities) == 5
    assert report.n_records == 500
    assert 2024 in report.years
    assert "mean" in report.old_score_stats
    assert "mean" in report.new_score_stats
    assert "estavel" in report.old_classification_counts
    assert "estavel" in report.new_classification_counts


def test_calibration_report_roundtrip(tmp_path: object) -> None:
    df = _make_synthetic_omni(n=100)
    report = build_calibration_report(df)
    report_df = calibration_report_to_dataframe(report)

    assert "type" in report_df.columns
    assert "name" in report_df.columns
    dist_rows = report_df[report_df["type"] == "distribution"]
    sens_rows = report_df[report_df["type"] == "sensitivity"]
    assert len(dist_rows) == 5
    assert len(sens_rows) == 5

    # Roundtrip parquet
    path = tmp_path / "report.parquet"  # type: ignore[operator]
    report_df.to_parquet(path, index=False)
    loaded = pd.read_parquet(path)
    assert len(loaded) == len(report_df)


def test_prepare_solar_only_dataframe():
    df = _make_synthetic_omni()
    data_array, var_names = prepare_solar_only_dataframe(df)

    assert data_array.ndim == 2
    assert data_array.shape[1] == 4  # kp, dst, bz, speed
    assert len(var_names) == 4
    assert data_array.shape[0] > 0
    assert not np.any(np.isnan(data_array))
