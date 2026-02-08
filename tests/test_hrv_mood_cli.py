"""Testes para o pipeline CLI genérico HRV + mood."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from darwin_heliobiology.pipelines.hrv_mood import build_hrv_mood_records, records_to_dataframe

EXPECTED_COLUMNS = [
    "subject_id",
    "timestamp",
    "window_minutes",
    "dataset",
    "mood_score",
    "mood_label",
    "hrv_rmssd",
    "hrv_sdnn",
    "hrv_pnn50",
    "hr_mean",
    "median_rr",
    "sample_entropy",
    "meta_samples",
]


def _synthetic_csv(tmp_path: Path, *, n_samples: int = 60) -> Path:
    """Cria CSV sintético com RR intervals e timestamps."""
    base = datetime(2025, 6, 1, 10, 0, tzinfo=timezone.utc)
    rows = []
    for i in range(n_samples):
        ts = base + timedelta(seconds=i)
        rr = 800.0 + (i % 10) * 5.0  # variação simples
        rows.append({"timestamp": ts.isoformat(), "rr_ms": rr})
    df = pd.DataFrame(rows)
    csv_path = tmp_path / "subject01.csv"
    df.to_csv(csv_path, index=False)
    return csv_path


def test_pipeline_produces_expected_schema(tmp_path: Path) -> None:
    csv_path = _synthetic_csv(tmp_path, n_samples=60)
    df = pd.read_csv(csv_path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    records = build_hrv_mood_records(
        subject_id="S01",
        dataset="test",
        rr_intervals_ms=df["rr_ms"].astype(float).tolist(),
        mood_responses={"mood": 0.5},
        scales={"mood": (0.0, 1.0)},
        timestamps=df["timestamp"].tolist(),
        window_minutes=1,
        min_samples=2,
    )

    assert len(records) > 0
    out_df = records_to_dataframe(records)
    assert list(out_df.columns) == EXPECTED_COLUMNS


def test_pipeline_csv_output(tmp_path: Path) -> None:
    csv_path = _synthetic_csv(tmp_path, n_samples=60)
    df = pd.read_csv(csv_path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    records = build_hrv_mood_records(
        subject_id="S01",
        dataset="test",
        rr_intervals_ms=df["rr_ms"].astype(float).tolist(),
        mood_responses={"mood": 0.3},
        scales={"mood": (0.0, 1.0)},
        timestamps=df["timestamp"].tolist(),
        window_minutes=1,
        min_samples=2,
    )

    out_df = records_to_dataframe(records)
    output_path = tmp_path / "output.csv"
    out_df.to_csv(output_path, index=False)

    reloaded = pd.read_csv(output_path)
    assert "hrv_rmssd" in reloaded.columns
    assert "mood_score" in reloaded.columns
    assert len(reloaded) == len(records)
