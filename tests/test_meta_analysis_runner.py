"""Testes para o orquestrador de metaanálises por domínio."""

from __future__ import annotations

from darwin_heliobiology.pipelines.meta_analysis_runner import (
    meta_results_to_dataframe,
    run_domain_meta_analyses,
    run_single_domain_meta,
)


def test_run_cardiovascular_meta_analysis() -> None:
    result = run_single_domain_meta("cardiovascular")
    assert result is not None
    assert result.domain == "cardiovascular"
    assert result.evidence_grade == "A"
    # Efeito combinado (log RR) deve ser positivo (RR > 1)
    assert result.result.pooled_effect > 0


def test_run_hrv_meta_analysis() -> None:
    result = run_single_domain_meta("hrv")
    assert result is not None
    assert result.domain == "hrv"
    assert result.evidence_grade == "B"
    # Fisher-z deve ser negativo (Kp ↑ → HRV ↓)
    assert result.result.pooled_effect < 0


def test_run_suicide_meta_analysis_high_heterogeneity() -> None:
    result = run_single_domain_meta("suicide")
    assert result is not None
    assert result.domain == "suicide"
    assert result.evidence_grade == "C"
    # Estudos ecológicos com efeitos muito diferentes → alta heterogeneidade
    assert result.result.i_squared > 50.0


def test_meta_results_to_dataframe_schema() -> None:
    results = run_domain_meta_analyses(["cardiovascular", "hrv", "suicide"])
    df = meta_results_to_dataframe(results)
    assert len(df) >= 2  # pelo menos 2 domínios com estudos suficientes
    expected_cols = {
        "domain",
        "evidence_grade",
        "pooled_effect",
        "ci_lower",
        "ci_upper",
        "p_value",
        "n_studies",
        "i_squared",
    }
    assert expected_cols <= set(df.columns)


def test_run_unknown_domain_returns_none() -> None:
    result = run_single_domain_meta("nonexistent")
    assert result is None
