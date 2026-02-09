"""Testes para metaanálise automatizada (DerSimonian-Laird)."""

import math

import pytest

from darwin_heliobiology.services.aletheia_validator import (
    AletheiaValidator,
    MetaAnalysisResult,
    StudyEffect,
)


@pytest.fixture
def validator() -> AletheiaValidator:
    return AletheiaValidator()


def _make_studies() -> list[StudyEffect]:
    """Cinco estudos sintéticos com efeitos moderados."""
    return [
        StudyEffect(study_id="s1", effect_size=0.30, variance=0.04, n=50, label="Kp-HRV A"),
        StudyEffect(study_id="s2", effect_size=0.25, variance=0.05, n=40, label="Kp-HRV B"),
        StudyEffect(study_id="s3", effect_size=0.35, variance=0.03, n=60, label="Kp-HRV C"),
        StudyEffect(study_id="s4", effect_size=0.20, variance=0.06, n=35, label="Kp-HRV D"),
        StudyEffect(study_id="s5", effect_size=0.28, variance=0.04, n=45, label="Kp-HRV E"),
    ]


def test_meta_analyze_returns_pooled_effect(validator: AletheiaValidator) -> None:
    studies = _make_studies()
    result = validator.meta_analyze(studies)

    assert isinstance(result, MetaAnalysisResult)
    # Efeito combinado deve estar no range dos efeitos individuais
    assert 0.15 <= result.pooled_effect <= 0.40
    assert result.pooled_ci_lower < result.pooled_effect
    assert result.pooled_effect < result.pooled_ci_upper


def test_meta_analyze_weights_match_studies(validator: AletheiaValidator) -> None:
    studies = _make_studies()
    result = validator.meta_analyze(studies)

    assert len(result.weights) == len(studies)
    assert all(w > 0 for w in result.weights)


def test_meta_analyze_heterogeneity_stats(validator: AletheiaValidator) -> None:
    studies = _make_studies()
    result = validator.meta_analyze(studies)

    assert result.q_statistic >= 0
    assert 0.0 <= result.i_squared <= 100.0
    assert result.tau_squared >= 0.0


def test_meta_analyze_single_study(validator: AletheiaValidator) -> None:
    study = StudyEffect(study_id="s1", effect_size=0.30, variance=0.04, n=50, label="solo")
    result = validator.meta_analyze([study])

    assert result.pooled_effect == pytest.approx(0.30, abs=1e-6)
    assert result.tau_squared == 0.0
    assert len(result.weights) == 1


def test_meta_analyze_empty_raises(validator: AletheiaValidator) -> None:
    with pytest.raises(ValueError, match="pelo menos 1 estudo"):
        validator.meta_analyze([])


def test_meta_analyze_high_heterogeneity(validator: AletheiaValidator) -> None:
    """Estudos com efeitos muito dispersos devem gerar I² elevado."""
    studies = [
        StudyEffect(study_id="s1", effect_size=0.80, variance=0.02, n=100, label="alto"),
        StudyEffect(study_id="s2", effect_size=-0.10, variance=0.02, n=100, label="negativo"),
        StudyEffect(study_id="s3", effect_size=0.50, variance=0.02, n=100, label="medio"),
    ]
    result = validator.meta_analyze(studies)
    assert result.i_squared > 50.0


def test_fisher_z_transform_roundtrip() -> None:
    r_original = 0.45
    study = AletheiaValidator.fisher_z_transform(r_original, n=50, study_id="t1", label="test")

    assert study.variance == pytest.approx(1.0 / 47.0, abs=1e-6)
    r_back = AletheiaValidator.inverse_fisher_z(study.effect_size)
    assert r_back == pytest.approx(r_original, abs=1e-6)


def test_fisher_z_transform_small_n_raises() -> None:
    with pytest.raises(ValueError, match="n >= 4"):
        AletheiaValidator.fisher_z_transform(0.5, n=3)


def test_heterogeneity_summary_labels(validator: AletheiaValidator) -> None:
    studies = _make_studies()
    result = validator.meta_analyze(studies)
    summary = AletheiaValidator.heterogeneity_summary(result)

    assert "Q =" in summary["q_statistic"]
    assert "I²" in summary["i_squared"]
    assert "τ²" in summary["tau_squared"]


def test_p_value_is_valid(validator: AletheiaValidator) -> None:
    studies = _make_studies()
    result = validator.meta_analyze(studies)

    assert 0.0 <= result.p_value <= 1.0
    assert not math.isnan(result.z_score)
