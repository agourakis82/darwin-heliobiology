"""Ingestão e cache de dados brutos NOAA SWPC."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

import pandas as pd

from darwin_heliobiology.core.solar_atlas import SolarAtlas


@dataclass(slots=True)
class NOAAIngestionResult:
    """Resultado da ingestão de dados brutos NOAA SWPC."""

    kp_path: Optional[Path]
    dst_path: Optional[Path]
    solar_wind_path: Optional[Path]
    imf_path: Optional[Path]
    total_records: int


def _persist_df(df: pd.DataFrame, path: Path) -> Path:
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".parquet":
        df.to_parquet(path, index=False)
    elif path.suffix == ".json":
        df.to_json(str(path), orient="records", force_ascii=False, indent=2)
    elif path.suffix == ".csv":
        df.to_csv(path, index=False)
    else:
        raise ValueError(f"Formato não suportado: {path.suffix}")
    return path


def fetch_and_persist_noaa(
    *,
    atlas: Optional[SolarAtlas] = None,
    hours: int = 24,
    output_dir: Path = Path("data/raw/noaa"),
    suffix: str = ".parquet",
) -> NOAAIngestionResult:
    """Baixa índices Kp, Dst, vento solar e IMF e persiste como arquivos brutos."""

    atlas = atlas or SolarAtlas()

    kp_series = atlas.fetch_kp_index(hours=hours)
    dst_series = atlas.fetch_dst_index(hours=hours)
    wind_samples = atlas.fetch_solar_wind(hours=hours)
    imf_vectors = atlas.fetch_imf(hours=hours)

    total = 0
    kp_path: Optional[Path] = None
    dst_path: Optional[Path] = None
    wind_path: Optional[Path] = None
    imf_path: Optional[Path] = None

    if kp_series:
        df_kp = pd.DataFrame([asdict(s) for s in kp_series])
        kp_path = _persist_df(df_kp, output_dir / f"kp{suffix}")
        total += len(kp_series)

    if dst_series:
        df_dst = pd.DataFrame([asdict(s) for s in dst_series])
        dst_path = _persist_df(df_dst, output_dir / f"dst{suffix}")
        total += len(dst_series)

    if wind_samples:
        df_wind = pd.DataFrame([asdict(s) for s in wind_samples])
        wind_path = _persist_df(df_wind, output_dir / f"solar_wind{suffix}")
        total += len(wind_samples)

    if imf_vectors:
        df_imf = pd.DataFrame([asdict(s) for s in imf_vectors])
        imf_path = _persist_df(df_imf, output_dir / f"imf{suffix}")
        total += len(imf_vectors)

    return NOAAIngestionResult(
        kp_path=kp_path,
        dst_path=dst_path,
        solar_wind_path=wind_path,
        imf_path=imf_path,
        total_records=total,
    )
