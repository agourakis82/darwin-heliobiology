"""Pipeline para unificar HRV e mood em janelas temporais."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, List, Mapping, Sequence

import pandas as pd

from darwin_heliobiology.features.hrv import HRVFeatures, extract_hrv_features
from darwin_heliobiology.preprocessing.mood import MoodScore, make_mood_score


@dataclass(slots=True)
class HRVMoodRecord:
    subject_id: str
    timestamp: datetime
    window_minutes: int
    hrv_features: HRVFeatures
    mood: MoodScore
    dataset: str
    metadata: Mapping[str, str]


def build_hrv_mood_records(
    *,
    subject_id: str,
    dataset: str,
    rr_intervals_ms: Sequence[float],
    mood_responses: Mapping[str, float],
    scales: Mapping[str, Sequence[float]],
    timestamps: Sequence[datetime],
    window_minutes: int = 30,
    min_samples: int = 2,
) -> List[HRVMoodRecord]:
    """Cria registros HRV+Mood alinhados usando janelas temporais regulares."""

    if len(rr_intervals_ms) != len(timestamps):
        raise ValueError("RR intervals e timestamps devem ter o mesmo tamanho")

    mood_score = make_mood_score(mood_responses, scales)
    df = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(timestamps),
            "rr_ms": rr_intervals_ms,
        }
    ).sort_values("timestamp")

    records: List[HRVMoodRecord] = []
    first_ts = df["timestamp"].iloc[0]
    grouper = pd.Grouper(
        key="timestamp", freq=f"{window_minutes}min", label="right", closed="right", origin=first_ts
    )
    for window_end, group in df.groupby(grouper):
        if not isinstance(window_end, pd.Timestamp):
            continue
        if len(group) < min_samples:
            continue

        rr_values = group["rr_ms"].astype(float).tolist()
        hrv_features = extract_hrv_features(rr_values)

        records.append(
            HRVMoodRecord(
                subject_id=subject_id,
                timestamp=window_end.to_pydatetime(),
                window_minutes=window_minutes,
                hrv_features=hrv_features,
                mood=mood_score,
                dataset=dataset,
                metadata={"samples": str(len(rr_values))},
            )
        )

    return records


def records_to_dataframe(records: Iterable[HRVMoodRecord]) -> pd.DataFrame:
    rows = []
    for rec in records:
        rows.append(
            {
                "subject_id": rec.subject_id,
                "timestamp": rec.timestamp,
                "window_minutes": rec.window_minutes,
                "dataset": rec.dataset,
                "mood_score": rec.mood.value,
                "mood_label": rec.mood.label,
                "hrv_rmssd": rec.hrv_features.rmssd,
                "hrv_sdnn": rec.hrv_features.sdnn,
                "hrv_pnn50": rec.hrv_features.pnn50,
                "hr_mean": rec.hrv_features.mean_hr,
                "median_rr": rec.hrv_features.median_rr,
                "sample_entropy": rec.hrv_features.sample_entropy,
                "meta_samples": rec.metadata.get("samples", ""),
            }
        )
    return pd.DataFrame(rows)
