"""Testes para o catálogo curado de estudos heliobiológicos."""

from __future__ import annotations

from darwin_heliobiology.datasets.study_catalog import (
    CURATED_STUDIES,
    get_studies_by_domain,
    studies_to_study_effects,
)


def test_curated_studies_all_have_doi() -> None:
    for study in CURATED_STUDIES:
        assert study.doi, f"Estudo {study.study_id} sem DOI"


def test_curated_studies_valid_grades() -> None:
    valid_grades = {"A", "B", "C", "D"}
    for study in CURATED_STUDIES:
        assert (
            study.evidence_grade in valid_grades
        ), f"Estudo {study.study_id} com grau inválido: {study.evidence_grade}"


def test_get_studies_by_domain_filters_correctly() -> None:
    cardio = get_studies_by_domain("cardiovascular")
    assert len(cardio) >= 2
    assert all(s.domain == "cardiovascular" for s in cardio)

    hrv = get_studies_by_domain("hrv")
    assert len(hrv) >= 2
    assert all(s.domain == "hrv" for s in hrv)

    suicide = get_studies_by_domain("suicide")
    assert len(suicide) >= 2
    assert all(s.domain == "suicide" for s in suicide)


def test_studies_to_study_effects_converts_r_type() -> None:
    hrv = get_studies_by_domain("hrv")
    effects = studies_to_study_effects(hrv)
    assert len(effects) >= 2
    for e in effects:
        assert e.variance > 0
        assert e.n > 0
        assert e.study_id


def test_studies_to_study_effects_converts_rr_type() -> None:
    cardio = get_studies_by_domain("cardiovascular")
    effects = studies_to_study_effects(cardio)
    # Pelo menos os 2 estudos com RR e IC devem ser convertidos
    rr_effects = [e for e in effects if e.effect_size > 0]  # log(RR) > 0 para RR > 1
    assert len(rr_effects) >= 1
