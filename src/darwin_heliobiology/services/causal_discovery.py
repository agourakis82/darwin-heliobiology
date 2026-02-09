"""Descoberta causal via PCMCI+ com priors heliobiológicos.

Integra variáveis solares (Kp, Dst, Bz) com biomarcadores autonômicos (RMSSD,
SDNN) e humor para identificar relações causais com lags temporais, usando
priors de domínio que codificam conhecimento heliobiológico (e.g., humor não
causa atividade solar).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# Variáveis solares (nunca causadas por variáveis biológicas)
SOLAR_VARS = {"kp", "dst", "bz"}
# Variáveis biológicas
BIO_VARS = {"rmssd", "sdnn", "mood_score"}


@dataclass(slots=True)
class CausalLink:
    """Aresta causal descoberta pelo PCMCI+."""

    source: str
    target: str
    lag: int
    coefficient: float
    p_value: float


@dataclass(slots=True)
class CausalDiscoveryResult:
    """Resultado consolidado da descoberta causal."""

    links: List[CausalLink]
    variable_names: List[str]
    tau_max: int
    method: str
    significant_links: List[CausalLink]
    metadata: Dict[str, Any] = field(default_factory=dict)


def prepare_causal_dataframe(
    solar_df: pd.DataFrame,
    hrv_df: pd.DataFrame,
    *,
    solar_cols: Optional[List[str]] = None,
    bio_cols: Optional[List[str]] = None,
    resample_freq: str = "h",
) -> Tuple[np.ndarray, List[str]]:
    """Alinha dados solares e HRV em array (T x N) para tigramite.

    Parameters
    ----------
    solar_df:
        DataFrame com coluna ``timestamp`` e variáveis solares.
    hrv_df:
        DataFrame com coluna ``timestamp`` e variáveis HRV/mood.
    solar_cols:
        Colunas solares a usar (default: kp_index, dst_nt, bz_gsm_nt).
    bio_cols:
        Colunas biológicas a usar (default: hrv_rmssd, hrv_sdnn, mood_score).
    resample_freq:
        Frequência de reamostragem (default: "h" = horário).

    Returns
    -------
    (data, var_names)
        Array numpy (T x N) e lista de nomes de variáveis.
    """
    solar_cols = solar_cols or ["kp_index", "dst_nt", "bz_gsm_nt"]
    bio_cols = bio_cols or ["hrv_rmssd", "hrv_sdnn", "mood_score"]

    solar = solar_df[["timestamp"] + solar_cols].copy()
    solar["timestamp"] = pd.to_datetime(solar["timestamp"])
    solar = solar.set_index("timestamp").resample(resample_freq).mean()

    bio = hrv_df[["timestamp"] + bio_cols].copy()
    bio["timestamp"] = pd.to_datetime(bio["timestamp"])
    bio = bio.set_index("timestamp").resample(resample_freq).mean()

    merged = solar.join(bio, how="inner").dropna()
    var_names_mapped: List[str] = []
    for col in solar_cols:
        short = col.replace("_index", "").replace("_nt", "").replace("_gsm", "")
        var_names_mapped.append(short)
    for col in bio_cols:
        short = col.replace("hrv_", "").replace("_score", "")
        var_names_mapped.append(short if short != "mood" else "mood_score")

    data = merged.values.astype(np.float64)
    return data, var_names_mapped


def build_helio_mood_priors(
    var_names: List[str],
    tau_max: int = 48,
) -> Dict[int, Dict[Tuple[int, int], Any]]:
    """Constrói link_assumptions para PCMCI+ com priors heliobiológicos.

    Regras de domínio:
    - Solar → Solar: autocorrelação permitida
    - Solar → Bio: permitido (lag 0..tau_max)
    - Bio → Solar: **proibido** (humor não causa atividade solar)
    - Bio → Bio: permitido
    """
    n = len(var_names)
    solar_indices = {i for i, v in enumerate(var_names) if v in SOLAR_VARS}
    bio_indices = {i for i, v in enumerate(var_names) if v in BIO_VARS}

    link_assumptions: Dict[int, Dict[Tuple[int, int], Any]] = {}

    for j in range(n):
        assumptions: Dict[Tuple[int, int], Any] = {}
        for i in range(n):
            for lag in range(0, tau_max + 1):
                if lag == 0 and i >= j:
                    # PCMCI+ contemporâneo: evitar duplicatas
                    continue
                key = (i, -lag)
                if i in bio_indices and j in solar_indices:
                    # Bio → Solar: proibido
                    assumptions[key] = ""
                else:
                    # Permitido
                    assumptions[key] = "-->"
        link_assumptions[j] = assumptions

    return link_assumptions


def run_pcmci_plus(
    data: np.ndarray,
    var_names: List[str],
    *,
    tau_max: int = 48,
    alpha: float = 0.05,
    method: str = "ParCorr",
    priors: Optional[Dict[int, Dict[Tuple[int, int], Any]]] = None,
) -> CausalDiscoveryResult:
    """Executa PCMCI+ via tigramite e retorna links causais.

    Parameters
    ----------
    data:
        Array (T x N) com dados alinhados temporalmente.
    var_names:
        Nomes das N variáveis.
    tau_max:
        Lag máximo a testar.
    alpha:
        Nível de significância.
    method:
        Teste de independência: "ParCorr" (linear) ou "CMIknn" (não-linear).
    priors:
        link_assumptions do tigramite (ver ``build_helio_mood_priors``).

    Returns
    -------
    CausalDiscoveryResult
    """
    try:
        from tigramite import data_processing as pp
        from tigramite.independence_tests.parcorr import ParCorr
        from tigramite.pcmci import PCMCI as TigramitePCMCI
    except ImportError as exc:
        raise ImportError(
            "tigramite é necessário para descoberta causal. " "Instale com: pip install tigramite"
        ) from exc

    dataframe = pp.DataFrame(data, var_names=var_names)

    if method == "ParCorr":
        cond_ind_test = ParCorr(significance="analytic")
    elif method == "CMIknn":
        from tigramite.independence_tests.cmiknn import CMIknn

        cond_ind_test = CMIknn(significance="shuffle_test", knn=0.1)
    else:
        raise ValueError(f"Método desconhecido: {method}. Use 'ParCorr' ou 'CMIknn'.")

    pcmci = TigramitePCMCI(dataframe=dataframe, cond_ind_test=cond_ind_test, verbosity=0)

    results = pcmci.run_pcmciplus(
        tau_max=tau_max,
        pc_alpha=alpha,
        link_assumptions=priors,
    )

    # Parsear grafo de resultados em CausalLinks
    graph = results["graph"]
    val_matrix = results["val_matrix"]
    p_matrix = results["p_matrix"]

    links: List[CausalLink] = []
    n_vars = len(var_names)

    for i in range(n_vars):
        for j in range(n_vars):
            for lag in range(tau_max + 1):
                edge = graph[i, j, lag]
                if edge not in ("", ""):
                    if edge in ("-->", "o-o", "x-x", "<->"):
                        links.append(
                            CausalLink(
                                source=var_names[i],
                                target=var_names[j],
                                lag=lag,
                                coefficient=float(val_matrix[i, j, lag]),
                                p_value=float(p_matrix[i, j, lag]),
                            )
                        )

    significant = [link for link in links if link.p_value < alpha]

    return CausalDiscoveryResult(
        links=links,
        variable_names=var_names,
        tau_max=tau_max,
        method=method,
        significant_links=significant,
        metadata={"alpha": alpha, "n_observations": data.shape[0], "n_variables": n_vars},
    )


def causal_results_to_dataframe(result: CausalDiscoveryResult) -> pd.DataFrame:
    """Converte links causais em DataFrame."""
    rows = []
    for link in result.links:
        rows.append(
            {
                "source": link.source,
                "target": link.target,
                "lag": link.lag,
                "coefficient": link.coefficient,
                "p_value": link.p_value,
                "significant": link.p_value < result.metadata.get("alpha", 0.05),
            }
        )
    return pd.DataFrame(rows)
