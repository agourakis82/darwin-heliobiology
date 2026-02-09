"""Testes para o AletheiaValidator.

Ranges de ScientificExpectation baseados em:
- r_individual geomag→HRV: 0.05–0.25 (Ong et al. 2022, PMC9233046)
- r_ecológico geomag→suicídio: 0.10–0.40 (Berk et al. 2006, doi:10.1002/bem.20190)
  Nota: r=0.69 (Gordon & Berk 2003) é agregado anual confundido por sazonalidade,
  não usar como expectativa.
"""

from darwin_heliobiology.services.aletheia_validator import AletheiaValidator, ScientificExpectation


def test_validate_correlation_exceeds_expected_range():
    validator = AletheiaValidator()
    # Range conservador baseado em literatura (efeitos individuais geomag→HRV)
    expectation = ScientificExpectation(description="Geomag vs. HRV", lower=0.05, upper=0.25)

    series_a = [1, 2, 3, 4, 5]
    series_b = [2, 3, 4, 5, 6]

    corr, within = validator.validate_correlation(series_a, series_b, expectation)

    assert corr > 0.9
    assert not within  # r~1.0 excede a faixa esperada (0.05–0.25)


def test_validate_correlation_detects_valid_range():
    validator = AletheiaValidator()
    # Range que comporta correlação alta (teste funcional, não claim científico)
    expectation = ScientificExpectation(description="Teste funcional", lower=0.3, upper=1.0)

    series_a = [1, 2, 3, 4, 5]
    series_b = [1.1, 2.0, 3.1, 4.0, 5.1]

    corr, within = validator.validate_correlation(series_a, series_b, expectation)

    assert corr >= expectation.lower
    assert within
