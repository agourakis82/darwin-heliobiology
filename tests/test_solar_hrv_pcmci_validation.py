"""Testes para validação PCMCI+ solar + HRV."""

from __future__ import annotations

from darwin_heliobiology.services.causal_discovery import (
    CausalDiscoveryResult,
    CausalLink,
    build_helio_mood_priors,
)


def test_priors_forbid_bio_to_solar() -> None:
    """Bio → Solar deve ser bloqueado nos priors heliobiológicos."""
    var_names = ["kp", "dst", "bz", "rmssd", "sdnn", "mood_score"]
    priors = build_helio_mood_priors(var_names, tau_max=24)

    # Índices solares: 0, 1, 2; bio: 3, 4, 5
    # Bio → Solar links devem ser proibidos (valor = "")
    for bio_idx in [3, 4, 5]:
        for solar_idx in [0, 1, 2]:
            for lag in range(0, 25):
                link_key = (bio_idx, -lag)
                if link_key in priors.get(solar_idx, {}):
                    assert priors[solar_idx][link_key] == "", (
                        f"Bio {var_names[bio_idx]} → Solar {var_names[solar_idx]} "
                        f"deveria ser bloqueado (lag={lag})"
                    )


def test_combined_pcmci_result_structure() -> None:
    """Verifica estrutura do CausalDiscoveryResult com variáveis mistas."""
    links = [
        CausalLink(source="kp", target="dst", lag=1, coefficient=0.34, p_value=0.001),
        CausalLink(source="kp", target="rmssd", lag=2, coefficient=-0.15, p_value=0.02),
    ]
    result = CausalDiscoveryResult(
        links=links,
        variable_names=["kp", "dst", "rmssd"],
        tau_max=24,
        method="ParCorr",
        significant_links=[links[0], links[1]],
    )
    assert len(result.significant_links) == 2
    assert result.variable_names == ["kp", "dst", "rmssd"]


def test_priors_allow_solar_to_bio() -> None:
    """Solar → Bio deve ser permitido (é a hipótese heliobiológica)."""
    var_names = ["kp", "dst", "rmssd", "mood_score"]
    priors = build_helio_mood_priors(var_names, tau_max=12)

    # Solar → Bio não deve estar bloqueado
    # Os priors devem permitir kp → rmssd
    bio_idx = 2  # rmssd
    solar_idx = 0  # kp
    # Se o link estiver no dict de priors para bio_idx, deve ser permitido
    if bio_idx in priors:
        for lag in range(1, 13):
            link_key = (solar_idx, -lag)
            if link_key in priors[bio_idx]:
                assert (
                    priors[bio_idx][link_key] != ""
                ), f"Solar kp → Bio rmssd deveria ser permitido (lag={lag})"
