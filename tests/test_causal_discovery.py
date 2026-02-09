"""Testes para descoberta causal PCMCI+ com priors heliobiológicos."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd

from darwin_heliobiology.services.causal_discovery import (
    CausalDiscoveryResult,
    build_helio_mood_priors,
    causal_results_to_dataframe,
    prepare_causal_dataframe,
    run_pcmci_plus,
)


def _make_solar_df(n: int = 200) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    timestamps = pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC")
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "kp_index": rng.uniform(0, 9, n),
            "dst_nt": rng.uniform(-200, 20, n),
            "bz_gsm_nt": rng.uniform(-15, 15, n),
        }
    )


def _make_hrv_df(n: int = 200) -> pd.DataFrame:
    rng = np.random.default_rng(43)
    timestamps = pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC")
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "hrv_rmssd": rng.uniform(20, 80, n),
            "hrv_sdnn": rng.uniform(30, 100, n),
            "mood_score": rng.uniform(0, 1, n),
        }
    )


def test_prepare_causal_dataframe() -> None:
    solar = _make_solar_df()
    hrv = _make_hrv_df()
    data, var_names = prepare_causal_dataframe(solar, hrv)

    assert data.ndim == 2
    assert data.shape[1] == 6  # 3 solares + 3 bio
    assert len(var_names) == 6
    assert data.shape[0] > 0


def test_prepare_causal_dataframe_custom_cols() -> None:
    solar = _make_solar_df()
    hrv = _make_hrv_df()
    data, var_names = prepare_causal_dataframe(
        solar,
        hrv,
        solar_cols=["kp_index"],
        bio_cols=["hrv_rmssd"],
    )
    assert data.shape[1] == 2
    assert len(var_names) == 2


def test_build_helio_mood_priors() -> None:
    var_names = ["kp", "dst", "bz", "rmssd", "sdnn", "mood_score"]
    priors = build_helio_mood_priors(var_names, tau_max=5)

    assert isinstance(priors, dict)
    assert len(priors) == 6  # uma entrada por variável-alvo

    # Bio → Solar deve ser proibido
    # var 0 = kp (solar), var 3 = rmssd (bio)
    kp_assumptions = priors[0]
    for lag in range(1, 6):
        key = (3, -lag)
        if key in kp_assumptions:
            assert kp_assumptions[key] == ""  # proibido

    # Solar → Bio deve ser permitido
    rmssd_assumptions = priors[3]
    key = (0, -1)
    if key in rmssd_assumptions:
        assert rmssd_assumptions[key] == "-->"


def test_run_pcmci_plus_with_mock() -> None:
    """Testa run_pcmci_plus com tigramite mockado para evitar dependência em CI."""
    import sys

    n_vars = 3
    tau_max = 2
    n_obs = 50
    data = np.random.default_rng(42).standard_normal((n_obs, n_vars))
    var_names = ["kp", "rmssd", "mood_score"]

    # Mock do grafo de resultado: uma aresta significativa kp→rmssd lag 1
    mock_graph = np.full((n_vars, n_vars, tau_max + 1), "", dtype="<U3")
    mock_graph[0, 1, 1] = "-->"

    mock_val = np.zeros((n_vars, n_vars, tau_max + 1))
    mock_val[0, 1, 1] = 0.35

    mock_p = np.ones((n_vars, n_vars, tau_max + 1))
    mock_p[0, 1, 1] = 0.01

    mock_results = {"graph": mock_graph, "val_matrix": mock_val, "p_matrix": mock_p}

    # Criar mocks para os módulos tigramite
    mock_pp = MagicMock()
    mock_pp.DataFrame.return_value = MagicMock()

    mock_parcorr_mod = MagicMock()
    mock_parcorr_mod.ParCorr.return_value = MagicMock()

    mock_pcmci_instance = MagicMock()
    mock_pcmci_instance.run_pcmciplus.return_value = mock_results

    mock_pcmci_mod = MagicMock()
    mock_pcmci_mod.PCMCI.return_value = mock_pcmci_instance

    # Injetar módulos mockados em sys.modules
    tigramite_mocks = {
        "tigramite": MagicMock(),
        "tigramite.data_processing": mock_pp,
        "tigramite.independence_tests": MagicMock(),
        "tigramite.independence_tests.parcorr": mock_parcorr_mod,
        "tigramite.pcmci": mock_pcmci_mod,
    }

    with patch.dict(sys.modules, tigramite_mocks):
        result = run_pcmci_plus(data, var_names, tau_max=tau_max, alpha=0.05)

    assert isinstance(result, CausalDiscoveryResult)
    assert len(result.significant_links) == 1
    assert result.significant_links[0].source == "kp"
    assert result.significant_links[0].target == "rmssd"
    assert result.significant_links[0].lag == 1


def test_causal_results_to_dataframe() -> None:
    from darwin_heliobiology.services.causal_discovery import CausalLink

    result = CausalDiscoveryResult(
        links=[
            CausalLink(source="kp", target="rmssd", lag=1, coefficient=0.35, p_value=0.01),
            CausalLink(source="dst", target="mood_score", lag=3, coefficient=0.15, p_value=0.12),
        ],
        variable_names=["kp", "dst", "rmssd", "mood_score"],
        tau_max=5,
        method="ParCorr",
        significant_links=[
            CausalLink(source="kp", target="rmssd", lag=1, coefficient=0.35, p_value=0.01)
        ],
        metadata={"alpha": 0.05},
    )
    df = causal_results_to_dataframe(result)

    assert len(df) == 2
    assert "source" in df.columns
    assert "significant" in df.columns
    assert bool(df.iloc[0]["significant"]) is True
    assert bool(df.iloc[1]["significant"]) is False
