"""Orquestração do pipeline HelioMind Index."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import pandas as pd

from darwin_heliobiology.core.solar_atlas import SolarAtlas
from darwin_heliobiology.metrics.helio_index import compute_helio_mind_index


def build_heliomind_dataframe(
    atlas: Optional[SolarAtlas] = None, *, hours: int = 24
) -> pd.DataFrame:
    """Constrói um DataFrame contendo o HelioMind Index para a janela informada."""

    atlas = atlas or SolarAtlas()
    snapshot = atlas.snapshot(hours=hours)
    result = compute_helio_mind_index(snapshot)

    record = {
        "timestamp": result.timestamp,
        "score": result.score,
        "classification": result.classification,
        "kp_activity": result.components.kp_activity,
        "dst_storm_intensity": result.components.dst_storm_intensity,
        "bz_reconnection": result.components.bz_reconnection,
        "solar_wind_pressure": result.components.solar_wind_pressure,
        "variability": result.components.variability,
        "alerts": json.dumps(result.alerts, ensure_ascii=False),
    }

    for key, value in (result.metadata or {}).items():
        record[f"meta_{key}"] = value

    return pd.DataFrame([record])


def persist_heliomind_dataframe(df: pd.DataFrame, output: Path) -> Path:
    """Salva o DataFrame em Parquet ou JSON conforme a extensão."""

    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    if output.suffix == ".parquet":
        df.to_parquet(output, index=False)
    elif output.suffix == ".json":
        df.to_json(str(output), orient="records", force_ascii=False, indent=2, lines=False)
    elif output.suffix == ".ndjson":
        df.to_json(str(output), orient="records", force_ascii=False, lines=True)
    elif output.suffix == ".csv":
        df.to_csv(output, index=False)
    else:
        raise ValueError(f"Formato não suportado: {output.suffix}")

    return output
