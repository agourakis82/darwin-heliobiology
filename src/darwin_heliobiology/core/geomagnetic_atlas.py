"""Atlas temporal de assinaturas geomagnéticas.

Agrupa dados OMNI2 em janelas temporais (diária, mensal, trimestral) e computa
perfis estatísticos que revelam padrões recorrentes de atividade geomagnética.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import pandas as pd


@dataclass(slots=True)
class GeomagneticSignature:
    """Assinatura geomagnética agregada para um período."""

    period_label: str
    mean_kp: float
    mean_dst: float
    mean_bz: float
    storm_count: int
    min_dst: float
    bz_southward_fraction: float


@dataclass(slots=True)
class AtlasResult:
    """Resultado do atlas temporal de assinaturas geomagnéticas."""

    signatures: List[GeomagneticSignature]
    resolution: str
    year_range: Tuple[int, int]
    metadata: Dict[str, Any]


_RESOLUTION_FREQ = {
    "daily": "D",
    "monthly": "ME",
    "quarterly": "QE",
}

_RESOLUTION_FORMAT = {
    "daily": "%Y-%m-%d",
    "monthly": "%Y-%m",
    "quarterly": None,
}


def _period_label(ts: pd.Timestamp, resolution: str) -> str:
    fmt = _RESOLUTION_FORMAT.get(resolution)
    if fmt is not None:
        return ts.strftime(fmt)
    # Quarterly: "2024-Q1"
    return f"{ts.year}-Q{ts.quarter}"


def build_geomagnetic_atlas(
    df: pd.DataFrame,
    resolution: str = "monthly",
) -> AtlasResult:
    """Constrói atlas temporal a partir de DataFrame OMNI2.

    Parameters
    ----------
    df:
        DataFrame com colunas ``timestamp``, ``kp_index``, ``dst_nt``, ``bz_gsm_nt``.
        Tipicamente produzido por :func:`datasets.omni._parse_omni2_text`.
    resolution:
        Resolução temporal: ``"daily"``, ``"monthly"`` ou ``"quarterly"``.

    Returns
    -------
    AtlasResult
        Lista de assinaturas geomagnéticas por período.
    """
    if resolution not in _RESOLUTION_FREQ:
        raise ValueError(f"Resolução inválida: {resolution}. Use: {list(_RESOLUTION_FREQ)}")

    required = {"timestamp", "kp_index", "dst_nt", "bz_gsm_nt"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Colunas ausentes no DataFrame: {missing}")

    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp")

    freq = _RESOLUTION_FREQ[resolution]
    grouper = pd.Grouper(key="timestamp", freq=freq)

    signatures: List[GeomagneticSignature] = []
    for period_end, group in df.groupby(grouper):
        if not isinstance(period_end, pd.Timestamp) or group.empty:
            continue

        kp = group["kp_index"].dropna()
        dst = group["dst_nt"].dropna()
        bz = group["bz_gsm_nt"].dropna()

        storm_count = int((kp >= 5.0).sum()) if not kp.empty else 0
        bz_south = float((bz < 0).mean()) if not bz.empty else 0.0

        signatures.append(
            GeomagneticSignature(
                period_label=_period_label(period_end, resolution),
                mean_kp=float(kp.mean()) if not kp.empty else 0.0,
                mean_dst=float(dst.mean()) if not dst.empty else 0.0,
                mean_bz=float(bz.mean()) if not bz.empty else 0.0,
                storm_count=storm_count,
                min_dst=float(dst.min()) if not dst.empty else 0.0,
                bz_southward_fraction=bz_south,
            )
        )

    years = sorted(df["timestamp"].dt.year.unique())
    year_range = (int(years[0]), int(years[-1])) if years else (0, 0)

    return AtlasResult(
        signatures=signatures,
        resolution=resolution,
        year_range=year_range,
        metadata={"total_records": len(df), "periods": len(signatures)},
    )


def atlas_to_dataframe(result: AtlasResult) -> pd.DataFrame:
    """Converte ``AtlasResult`` em DataFrame para persistência."""
    rows = []
    for sig in result.signatures:
        rows.append(
            {
                "period_label": sig.period_label,
                "mean_kp": sig.mean_kp,
                "mean_dst": sig.mean_dst,
                "mean_bz": sig.mean_bz,
                "storm_count": sig.storm_count,
                "min_dst": sig.min_dst,
                "bz_southward_fraction": sig.bz_southward_fraction,
            }
        )
    df = pd.DataFrame(rows)
    df.attrs["resolution"] = result.resolution
    df.attrs["year_range"] = f"{result.year_range[0]}-{result.year_range[1]}"
    return df
