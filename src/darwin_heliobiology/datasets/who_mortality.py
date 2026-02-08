"""Ingestão de dados de mortalidade da WHO (Mortality Database)."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional
from zipfile import ZipFile

import pandas as pd
import requests

DEFAULT_TIMEOUT = 60

WHO_MORTALITY_URLS: Dict[str, str] = {
    "icd10_part1": (
        "https://cdn.who.int/media/docs/default-source/world-health-data-platform"
        "/mortality-raw-data/morticd10_part1.zip"
    ),
    "icd10_part2": (
        "https://cdn.who.int/media/docs/default-source/world-health-data-platform"
        "/mortality-raw-data/morticd10_part2.zip"
    ),
    "icd10_part3": (
        "https://cdn.who.int/media/docs/default-source/world-health-data-platform"
        "/mortality-raw-data/morticd10_part3.zip"
    ),
    "icd10_part4": (
        "https://cdn.who.int/media/docs/default-source/world-health-data-platform"
        "/mortality-raw-data/morticd10_part4.zip"
    ),
    "icd10_part5": (
        "https://cdn.who.int/media/docs/default-source/world-health-data-platform"
        "/mortality-raw-data/morticd10_part5.zip"
    ),
    "icd10_part6": (
        "https://cdn.who.int/media/docs/default-source/world-health-data-platform"
        "/mortality-raw-data/morticd10_part6.zip"
    ),
    "population": (
        "https://cdn.who.int/media/docs/default-source/world-health-data-platform"
        "/mortality-raw-data/pop.zip"
    ),
    "country_codes": (
        "https://cdn.who.int/media/docs/default-source/world-health-data-platform"
        "/mortality-raw-data/country_codes.zip"
    ),
}

# ICD-10: autolesão intencional (X60-X84) e eventos de intenção indeterminada (Y10-Y34)
SUICIDE_ICD10_PREFIXES: List[str] = [f"X{i}" for i in range(60, 85)] + [
    f"Y{i}" for i in range(10, 35)
]


@dataclass(slots=True)
class WHOIngestionResult:
    """Resultado da ingestão de dados WHO mortality."""

    output_dir: Path
    files_extracted: List[str]
    total_size_bytes: int


def _download_and_extract_zip(
    url: str,
    output_dir: Path,
    *,
    session: Optional[requests.Session] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> List[str]:
    """Baixa ZIP e extrai conteúdo para ``output_dir``."""
    sess = session or requests.Session()
    response = sess.get(url, timeout=timeout)
    response.raise_for_status()

    output_dir.mkdir(parents=True, exist_ok=True)
    extracted: List[str] = []
    with ZipFile(BytesIO(response.content)) as archive:
        for name in archive.namelist():
            archive.extract(name, output_dir)
            extracted.append(name)
    return extracted


def fetch_who_mortality(
    *,
    parts: Optional[List[str]] = None,
    output_dir: Path = Path("data/raw/who"),
    session: Optional[requests.Session] = None,
    include_population: bool = True,
) -> WHOIngestionResult:
    """Baixa CSVs de mortalidade da WHO e extrai para ``output_dir``.

    Parameters
    ----------
    parts:
        Chaves de partes específicas (ex: ``["icd10_part5", "icd10_part6"]``).
        Se ``None``, baixa todas as partes ICD-10.
    include_population:
        Também baixa dados populacionais para cálculo de taxas.
    """
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    keys_to_fetch = parts or [k for k in WHO_MORTALITY_URLS if k.startswith("icd10")]
    if include_population and "population" not in keys_to_fetch:
        keys_to_fetch.append("population")

    all_extracted: List[str] = []
    for key in keys_to_fetch:
        url = WHO_MORTALITY_URLS[key]
        files = _download_and_extract_zip(url, output_dir, session=session)
        all_extracted.extend(files)

    total_size = sum(
        (output_dir / f).stat().st_size for f in all_extracted if (output_dir / f).exists()
    )

    return WHOIngestionResult(
        output_dir=output_dir,
        files_extracted=all_extracted,
        total_size_bytes=total_size,
    )


def filter_suicide_mortality(csv_path: Path) -> pd.DataFrame:
    """Filtra CSV de mortalidade WHO para códigos ICD-10 de suicídio."""
    df = pd.read_csv(csv_path)
    cause_col = "Cause" if "Cause" in df.columns else "cause"
    mask = df[cause_col].astype(str).str[:3].isin(SUICIDE_ICD10_PREFIXES)
    return df[mask].copy()
