from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd

from darwin_heliobiology.pipelines.hrv_mood import build_hrv_mood_records, records_to_dataframe


def test_build_hrv_mood_records_generates_windows():
    base_ts = datetime(2025, 1, 1, 8, 0, tzinfo=timezone.utc)
    rr = [900 + ((-1) ** i) * 20 for i in range(12)]
    timestamps = [base_ts + timedelta(minutes=i) for i in range(len(rr))]
    responses = {"PANAS_pos": 4, "PANAS_neg": 1}
    scales = {"PANAS_pos": (1, 5), "PANAS_neg": (1, 5)}

    records = build_hrv_mood_records(
        subject_id="S1",
        dataset="synthetic",
        rr_intervals_ms=rr,
        mood_responses=responses,
        scales=scales,
        timestamps=timestamps,
        window_minutes=3,
    )
    assert len(records) == 4
    df = records_to_dataframe(records)
    assert isinstance(df, pd.DataFrame)
    assert "hrv_rmssd" in df.columns
    assert (df["dataset"] == "synthetic").all()
