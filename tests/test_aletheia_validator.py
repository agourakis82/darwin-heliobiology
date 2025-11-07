"""Testes para o AletheiaValidator."""

from darwin_heliobiology.services.aletheia_validator import AletheiaValidator, ScientificExpectation


def test_validate_correlation_exceeds_expected_range():
    validator = AletheiaValidator()
    expectation = ScientificExpectation(description="Geomag vs. suicídio", lower=0.3, upper=0.8)

    series_a = [1, 2, 3, 4, 5]
    series_b = [2, 3, 4, 5, 6]

    corr, within = validator.validate_correlation(series_a, series_b, expectation)

    assert corr > 0.9
    assert not within


def test_validate_correlation_detects_valid_range():
    validator = AletheiaValidator()
    expectation = ScientificExpectation(description="Geomag vs. suicídio", lower=0.3, upper=1.0)

    series_a = [1, 2, 3, 4, 5]
    series_b = [1.1, 2.0, 3.1, 4.0, 5.1]

    corr, within = validator.validate_correlation(series_a, series_b, expectation)

    assert corr >= expectation.lower
    assert within

