"""Pipeline para unificar HRV e mood em janelas temporais."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Iterator, List, Mapping, Sequence

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


def _rolling_windows(
    rr_stream: Sequence[float], samples_per_window: int
) -> Iterator[Sequence[float]]:
    for idx in range(0, len(rr_stream) - samples_per_window + 1, samples_per_window):
        yield rr_stream[idx : idx + samples_per_window]


def build_hrv_mood_records(
    *,
    subject_id: str,
    dataset: str,
    rr_intervals_ms: Sequence[float],
    mood_responses: Mapping[str, float],
    scales: Mapping[str, Sequence[float]],
    timestamps: Sequence[datetime],
    window_minutes: int = 30,
) -> List[HRVMoodRecord]:
    """Cria registros HRV+Mood alinhados.

    Parameters
    ----------
    rr_intervals_ms: sequências RR pré-filtradas (mesmo tamanho que timestamps).
    timestamps: timestamps correspondentes a cada RR.
    mood_responses: respostas cruas (ex: {"PANAS_pos": 4}).
    """

    if len(rr_intervals_ms) != len(timestamps):
        raise ValueError("RR intervals e timestamps devem ter o mesmo tamanho")

    samples_per_window = max(1, int(window_minutes))
    mood_score = make_mood_score(mood_responses, scales)

    records: List[HRVMoodRecord] = []
    rr_list = list(rr_intervals_ms)
    ts_list = list(timestamps)

    for window_index, window_rr in enumerate(_rolling_windows(rr_list, samples_per_window)):
        end_timestamp = ts_list[min(len(ts_list) - 1, (window_index + 1) * samples_per_window - 1)]
        hrv_features = extract_hrv_features(window_rr)
        records.append(
            HRVMoodRecord(
                subject_id=subject_id,
                timestamp=end_timestamp,
                window_minutes=window_minutes,
                hrv_features=hrv_features,
                mood=mood_score,
                dataset=dataset,
                metadata={"windows": str(samples_per_window)},
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
                "meta_windows": rec.metadata.get("windows", ""),
            }
        )
    return pd.DataFrame(rows)
