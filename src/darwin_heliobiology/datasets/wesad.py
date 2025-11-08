"""Utilidades para ingestão do dataset WESAD (Wearable Stress and Affect Detection)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List
from zipfile import ZipFile

import pandas as pd

from darwin_heliobiology.pipelines.hrv_mood import (
    HRVMoodRecord,
    build_hrv_mood_records,
    records_to_dataframe,
)

WESAD_DOWNLOAD_URL = "https://uni-siegen.sciebo.de/s/pYjguvSJDKcbpqs/download"
DEFAULT_SCALES = {"PANAS_pos": (1.0, 5.0), "PANAS_neg": (1.0, 5.0)}

LABEL_RESPONSES: Dict[str, Dict[str, float]] = {
    "baseline": {"PANAS_pos": 4.2, "PANAS_neg": 1.2},
    "stress": {"PANAS_pos": 2.2, "PANAS_neg": 3.8},
    "amusement": {"PANAS_pos": 4.5, "PANAS_neg": 1.5},
}

NUMERIC_LABELS = {
    "1": "baseline",
    "2": "stress",
    "3": "amusement",
    "0": "baseline",
}


@dataclass(slots=True)
class WESADIngestionResult:
    output_path: Path
    records: List[HRVMoodRecord]


def download_wesad(
    destination: Path, *, url: str = WESAD_DOWNLOAD_URL, chunk_size: int = 2**20
) -> Path:
    """Baixa o dataset WESAD para ``destination``.

    O download real não é coberto pelos testes automatizados; utilize ``url`` customizado
    para injetar artefatos locais durante o desenvolvimento.
    """

    import requests

    destination = destination.expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)

    response = requests.get(url, stream=True, timeout=60)
    response.raise_for_status()

    with destination.open("wb") as fp:
        for chunk in response.iter_content(chunk_size=chunk_size):
            fp.write(chunk)
    return destination


def extract_wesad(zip_path: Path, extract_to: Path) -> Path:
    extract_to.mkdir(parents=True, exist_ok=True)
    with ZipFile(zip_path) as archive:
        archive.extractall(extract_to)
    return extract_to


def _sanitize_label(raw_label: str) -> str | None:
    key = raw_label.strip().lower()
    if key in LABEL_RESPONSES:
        return key
    if raw_label in NUMERIC_LABELS:
        return NUMERIC_LABELS[raw_label]
    return None


def _split_by_label(df: pd.DataFrame) -> Iterable[pd.DataFrame]:
    if "label" not in df.columns:
        yield df
        return
    grouped = df.groupby("label")
    for _, group in grouped:
        yield group


def _records_from_rr_csv(
    csv_path: Path, *, subject_id: str, dataset: str, window_minutes: int, min_samples: int
) -> List[HRVMoodRecord]:
    df = pd.read_csv(csv_path)
    if "timestamp" not in df.columns or "rr_ms" not in df.columns:
        raise ValueError(f"Arquivo {csv_path} precisa conter colunas timestamp e rr_ms")

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    records: List[HRVMoodRecord] = []

    for segment in _split_by_label(df):
        label_col = segment.get("label")
        if label_col is None:
            label_name = "baseline"
        else:
            raw_label = str(label_col.iloc[0])
            label_name = _sanitize_label(raw_label) or "baseline"

        responses = LABEL_RESPONSES.get(label_name, LABEL_RESPONSES["baseline"])
        records.extend(
            build_hrv_mood_records(
                subject_id=subject_id,
                dataset=dataset,
                rr_intervals_ms=segment["rr_ms"].astype(float).tolist(),
                mood_responses=responses,
                scales=DEFAULT_SCALES,
                timestamps=segment["timestamp"].tolist(),
                window_minutes=window_minutes,
                min_samples=min_samples,
            )
        )
    return records


def build_wesad_hrv_mood(
    *,
    root: Path,
    output_path: Path,
    window_minutes: int = 5,
    min_samples: int = 30,
) -> WESADIngestionResult:
    """Gera arquivo de features HRV+mood a partir do conteúdo extraído do WESAD.

    Espera encontrar arquivos ``rr.csv`` (ou ``rr_intervals.csv``) dentro de cada diretório
    de participante (``S2/`` etc) com colunas ``timestamp``, ``rr_ms`` e ``label``.
    """

    root = root.expanduser().resolve()
    output_path = output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    records: List[HRVMoodRecord] = []
    for subject_dir in sorted(root.glob("S*/")):
        subject_id = subject_dir.name
        candidates = [subject_dir / "rr.csv", subject_dir / "rr_intervals.csv"]
        csv_file = next((path for path in candidates if path.exists()), None)
        if csv_file is None:
            continue
        records.extend(
            _records_from_rr_csv(
                csv_file,
                subject_id=subject_id,
                dataset="wesad",
                window_minutes=window_minutes,
                min_samples=min_samples,
            )
        )

    df = records_to_dataframe(records)

    if output_path.suffix == ".parquet":
        df.to_parquet(output_path, index=False)
    elif output_path.suffix == ".json":
        df.to_json(output_path, orient="records", force_ascii=False, indent=2)
    else:
        df.to_csv(output_path, index=False)

    return WESADIngestionResult(output_path=output_path, records=records)


__all__ = [
    "WESAD_DOWNLOAD_URL",
    "DEFAULT_SCALES",
    "LABEL_RESPONSES",
    "download_wesad",
    "extract_wesad",
    "build_wesad_hrv_mood",
    "WESADIngestionResult",
]
