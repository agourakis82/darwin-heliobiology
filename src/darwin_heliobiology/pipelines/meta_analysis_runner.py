"""Orquestrador de metaanálises por domínio heliobiológico.

Roda metaanálises DerSimonian-Laird usando o catálogo curado de estudos
(datasets/study_catalog.py) e o motor AletheiaValidator.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd

from darwin_heliobiology.datasets.study_catalog import (
    get_studies_by_domain,
    studies_to_study_effects,
)
from darwin_heliobiology.services.aletheia_validator import (
    AletheiaValidator,
    MetaAnalysisResult,
)


@dataclass(slots=True)
class DomainMetaResult:
    """Resultado de metaanálise para um domínio específico."""

    domain: str
    evidence_grade: str
    result: MetaAnalysisResult
    interpretation: str
    caveats: List[str] = field(default_factory=list)


# ── Domínios e configuração ─────────────────────────────────────────────────

_DOMAIN_CONFIG: Dict[str, Dict[str, Any]] = {
    "cardiovascular": {
        "grade": "A",
        "interpretation_positive": (
            "Efeito combinado indica associação significativa entre atividade "
            "geomagnética e risco cardiovascular (RR > 1)."
        ),
        "interpretation_null": (
            "Efeito combinado não atinge significância estatística para "
            "associação geomag → cardiovascular."
        ),
        "caveats": [
            "Heterogeneidade entre estudos pode refletir diferenças geográficas e metodológicas.",
            "A maioria dos estudos é retrospectiva; causalidade não é demonstrada.",
        ],
    },
    "hrv": {
        "grade": "B",
        "interpretation_positive": (
            "Efeito combinado indica redução de HRV (RMSSD, SDNN) durante "
            "alta atividade geomagnética."
        ),
        "interpretation_null": ("Efeito combinado não atinge significância para HRV × geomag."),
        "caveats": [
            "Ong 2022 (n=809) domina o resultado; outros estudos têm n pequeno.",
            "Alabdulgader 2018 (n=16) não corrige autocorrelação — efeito provavelmente superestimado.",
            "Efeito real é clinicamente modesto (~15ms RMSSD por IQR de Kp).",
        ],
    },
    "suicide": {
        "grade": "C",
        "interpretation_positive": (
            "Efeito combinado sugere associação ecológica, mas com alta "
            "heterogeneidade — resultado NÃO confiável."
        ),
        "interpretation_null": ("Sem evidência de associação robusta geomag → suicídio."),
        "caveats": [
            "Falácia ecológica: correlações populacionais ≠ efeito individual.",
            "Confounding sazonal: suicídio tem pico primaveral que co-varia com atividade solar.",
            "Gordon 2003 (r=0.69) não controla sazonalidade — provavelmente espúrio.",
            "Kay 1994 nunca replicado.",
            "Viés de publicação: estudos negativos não publicados neste campo.",
        ],
    },
}


# ── Funções principais ──────────────────────────────────────────────────────


def run_single_domain_meta(
    domain: str,
    *,
    validator: Optional[AletheiaValidator] = None,
) -> Optional[DomainMetaResult]:
    """Roda metaanálise para um domínio.  Retorna None se < 2 efeitos combináveis."""
    v = validator or AletheiaValidator()
    config = _DOMAIN_CONFIG.get(domain)
    if config is None:
        return None

    studies = get_studies_by_domain(domain)
    effects = studies_to_study_effects(studies)

    if len(effects) < 2:
        return None

    result = v.meta_analyze(effects)
    sig = result.p_value < 0.05

    interpretation = config["interpretation_positive"] if sig else config["interpretation_null"]

    return DomainMetaResult(
        domain=domain,
        evidence_grade=config["grade"],
        result=result,
        interpretation=interpretation,
        caveats=config["caveats"],
    )


def run_domain_meta_analyses(
    domains: Optional[List[str]] = None,
) -> List[DomainMetaResult]:
    """Roda metaanálises para todos os domínios solicitados."""
    target_domains = domains or list(_DOMAIN_CONFIG.keys())
    validator = AletheiaValidator()
    results: List[DomainMetaResult] = []
    for domain in target_domains:
        r = run_single_domain_meta(domain, validator=validator)
        if r is not None:
            results.append(r)
    return results


def meta_results_to_dataframe(results: List[DomainMetaResult]) -> pd.DataFrame:
    """Converte resultados em DataFrame para persistência."""
    rows: List[Dict[str, Any]] = []
    for r in results:
        het = AletheiaValidator.heterogeneity_summary(r.result)
        rows.append(
            {
                "domain": r.domain,
                "evidence_grade": r.evidence_grade,
                "pooled_effect": r.result.pooled_effect,
                "ci_lower": r.result.pooled_ci_lower,
                "ci_upper": r.result.pooled_ci_upper,
                "p_value": r.result.p_value,
                "z_score": r.result.z_score,
                "i_squared": r.result.i_squared,
                "tau_squared": r.result.tau_squared,
                "q_statistic": r.result.q_statistic,
                "n_studies": len(r.result.studies),
                "interpretation": r.interpretation,
                "heterogeneity": het["i_squared"],
            }
        )
    return pd.DataFrame(rows)


def print_meta_summary(results: List[DomainMetaResult]) -> None:
    """Imprime resumo legível das metaanálises."""
    print(f"\n{'=' * 65}")
    print("Metaanálise por Domínio — Estudos Curados")
    print(f"{'=' * 65}")

    for r in results:
        het = AletheiaValidator.heterogeneity_summary(r.result)
        sig = (
            "***"
            if r.result.p_value < 0.001
            else "**" if r.result.p_value < 0.01 else "*" if r.result.p_value < 0.05 else "ns"
        )

        print(f"\n--- {r.domain.upper()} (Grau {r.evidence_grade}) ---")
        print(f"  Efeito combinado: {r.result.pooled_effect:.4f}")
        print(f"  IC 95%: [{r.result.pooled_ci_lower:.4f}, {r.result.pooled_ci_upper:.4f}]")
        print(f"  z = {r.result.z_score:.3f}, p = {r.result.p_value:.4f} {sig}")
        print(f"  {het['i_squared']}")
        print(f"  Estudos: {len(r.result.studies)}")
        print(f"  Interpretação: {r.interpretation}")
        if r.caveats:
            print("  Ressalvas:")
            for c in r.caveats:
                print(f"    • {c}")

    print(f"\n{'=' * 65}\n")
