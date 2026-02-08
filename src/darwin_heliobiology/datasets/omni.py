"""Ingestão de dados OMNI2 hourly (NASA OMNIWeb).

Baixa arquivos anuais de ``https://spdf.gsfc.nasa.gov/pub/data/omni/low_res_omni/``
e parseia o formato fixed-width OMNI2 em DataFrame.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import requests

OMNI2_BASE_URL = "https://spdf.gsfc.nasa.gov/pub/data/omni/low_res_omni"
DEFAULT_TIMEOUT = 30

# Mapeamento coluna 0-indexed → nome semântico (referência: omni2.text)
# Col 1=Year, 2=DOY, 3=Hour, 13=Bx, 16=By_GSM, 17=Bz_GSM,
# 24=Proton density, 25=Speed, 29=Flow pressure, 39=Kp, 41=Dst
OMNI2_COL_MAP: Dict[int, str] = {
    0: "year",
    1: "doy",
    2: "hour",
    12: "bx_gsm_nt",
    15: "by_gsm_nt",
    16: "bz_gsm_nt",
    23: "proton_density_pcm3",
    24: "speed_kms",
    28: "flow_pressure_npa",
    38: "kp_index",
    40: "dst_nt",
}

# Valores de preenchimento (fill) que indicam dados ausentes
FILL_VALUES: Dict[str, float] = {
    "bx_gsm_nt": 999.9,
    "by_gsm_nt": 999.9,
    "bz_gsm_nt": 999.9,
    "speed_kms": 9999.0,
    "proton_density_pcm3": 999.9,
    "flow_pressure_npa": 99.99,
    "kp_index": 99.0,
    "dst_nt": 99999.0,
}


@dataclass(slots=True)
class OMNIIngestionResult:
    """Resultado da ingestão de dados OMNI2."""

    output_path: Path
    total_records: int
    years: List[int]


def _download_omni2_year(
    year: int,
    *,
    session: Optional[requests.Session] = None,
    base_url: str = OMNI2_BASE_URL,
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    """Baixa um ano de dados OMNI2 hourly, retorna texto bruto."""
    sess = session or requests.Session()
    url = f"{base_url}/omni2_{year}.dat"
    response = sess.get(url, timeout=timeout)
    response.raise_for_status()
    return response.text


def _parse_omni2_text(raw_text: str) -> pd.DataFrame:
    """Parseia texto OMNI2 fixed-width em DataFrame tipado.

    O formato OMNI2 usa colunas separadas por espaço com ~55 campos por linha.
    Seleciona apenas as colunas relevantes, constrói timestamp a partir de
    year + DOY + hour, e substitui fill values por NaN.
    """
    df_raw = pd.read_csv(StringIO(raw_text), sep=r"\s+", header=None)

    # Selecionar e renomear colunas relevantes
    selected = {name: df_raw[col_idx] for col_idx, name in OMNI2_COL_MAP.items()}
    df = pd.DataFrame(selected)

    # Construir timestamp: year + day_of_year + hour → datetime UTC
    df["timestamp"] = pd.to_datetime(
        df["year"].astype(int).astype(str) + "-" + df["doy"].astype(int).astype(str).str.zfill(3),
        format="%Y-%j",
    ) + pd.to_timedelta(df["hour"].astype(int), unit="h")
    df["timestamp"] = df["timestamp"].dt.tz_localize("UTC")

    # Remover colunas auxiliares
    df = df.drop(columns=["year", "doy", "hour"])

    # Converter tipos e substituir fill values por NaN
    for col, fill_val in FILL_VALUES.items():
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            df.loc[df[col] >= fill_val, col] = np.nan

    return df


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


def fetch_and_persist_omni(
    *,
    years: List[int],
    output_dir: Path = Path("data/raw/nasa_omni"),
    suffix: str = ".parquet",
    session: Optional[requests.Session] = None,
) -> OMNIIngestionResult:
    """Baixa dados OMNI2 hourly para os anos solicitados e persiste."""
    frames: List[pd.DataFrame] = []
    for year in years:
        raw = _download_omni2_year(year, session=session)
        df = _parse_omni2_text(raw)
        frames.append(df)

    combined = pd.concat(frames, ignore_index=True)

    output_dir_resolved = Path(output_dir).expanduser().resolve()
    output_path = output_dir_resolved / f"omni2_hourly{suffix}"
    _persist_df(combined, output_path)

    return OMNIIngestionResult(
        output_path=output_path,
        total_records=len(combined),
        years=years,
    )
