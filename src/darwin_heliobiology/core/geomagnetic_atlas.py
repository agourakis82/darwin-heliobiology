"""Atlas temporal de assinaturas geomagnéticas.

Agrupa dados OMNI2 em janelas temporais (diária, mensal, trimestral) e computa
perfis estatísticos que revelam padrões recorrentes de atividade geomagnética.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import pandas as pd

from darwin_heliobiology.datasets.omni import ensure_kp_scale


@dataclass(slots=True)
class GeomagneticSignature:
    """Assinatura geomagnética agregada para um período."""

    period_label: str
    mean_kp: float
    mean_dst: float
    mean_bz: float
    storm_hours: int  # horas com Kp ≥ 5 (apenas horas com Kp válido)
    min_dst: float
    bz_southward_fraction: float
    valid_hours: int = 0  # horas com Kp válido (denominador de storm_hours)


@dataclass(slots=True)
class AtlasResult:
    """Resultado do atlas temporal de assinaturas geomagnéticas."""

    signatures: List[GeomagneticSignature]
    resolution: str
    year_range: Tuple[int, int]
    metadata: Dict[str, Any]


#: Limiar de tempestade geomagnética (Kp real, escala 0–9).
STORM_KP = 5.0

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
    # Kp legado (×10) é levado para 0–9; Kp ≥ 5 só faz sentido na escala real.
    df["kp_index"] = ensure_kp_scale(df["kp_index"])
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

        # Ausente NUNCA vira 0: sem dado válido a estatística é NaN.
        storm_hours = int((kp >= STORM_KP).sum())
        bz_south = float((bz < 0).mean()) if not bz.empty else float("nan")
        nan = float("nan")

        signatures.append(
            GeomagneticSignature(
                period_label=_period_label(period_end, resolution),
                mean_kp=float(kp.mean()) if not kp.empty else nan,
                mean_dst=float(dst.mean()) if not dst.empty else nan,
                mean_bz=float(bz.mean()) if not bz.empty else nan,
                storm_hours=storm_hours,
                min_dst=float(dst.min()) if not dst.empty else nan,
                bz_southward_fraction=bz_south,
                valid_hours=len(kp),
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
                "storm_hours": sig.storm_hours,
                "valid_hours": sig.valid_hours,
                "min_dst": sig.min_dst,
                "bz_southward_fraction": sig.bz_southward_fraction,
            }
        )
    df = pd.DataFrame(rows)
    df.attrs["resolution"] = result.resolution
    df.attrs["year_range"] = f"{result.year_range[0]}-{result.year_range[1]}"
    return df
