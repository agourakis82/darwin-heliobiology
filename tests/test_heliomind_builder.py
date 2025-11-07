from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timedelta, timezone

import pandas as pd

from darwin_heliobiology.models.solar import (
    IMFVector,
    SolarIndex,
    SolarObservation,
    SolarWindSample,
)
from darwin_heliobiology.pipelines.heliomind_builder import (
    build_heliomind_dataframe,
    persist_heliomind_dataframe,
)


class DummyAtlas:
    def __init__(self, observation: SolarObservation) -> None:
        self._observation = observation

    def snapshot(self, hours: int = 24) -> SolarObservation:  # noqa: D401 - interface simulada
        return self._observation


def _dummy_observation() -> SolarObservation:
    base = datetime(2025, 1, 1, 6, 0, tzinfo=timezone.utc)
    kp = [
        SolarIndex(timestamp=base - timedelta(minutes=idx), value=4.5, label="Kp")
        for idx in range(4)
    ]
    dst = [
        SolarIndex(timestamp=base - timedelta(hours=idx), value=-80.0, label="Dst")
        for idx in range(4)
    ]
    wind = [
        SolarWindSample(
            timestamp=base - timedelta(minutes=idx),
            speed_kms=550.0,
            density_pcm3=7.5,
            temperature_k=120000.0,
        )
        for idx in range(4)
    ]
    imf = [
        IMFVector(
            timestamp=base - timedelta(minutes=idx),
            bx_nt=2.0,
            by_nt=-3.0,
            bz_nt=-10.0,
            bt_nt=12.0,
        )
        for idx in range(4)
    ]
    metadata = {"window_hours": 12, "retrieved_at": base.isoformat()}
    return SolarObservation(
        kp_series=kp, dst_series=dst, solar_wind=wind, imf=imf, metadata=metadata
    )


def test_build_heliomind_dataframe_flattens_components() -> None:
    observation = _dummy_observation()
    atlas = DummyAtlas(observation)

    df = build_heliomind_dataframe(atlas=atlas, hours=12)

    assert list(df.columns)[:5] == [
        "timestamp",
        "score",
        "classification",
        "kp_activity",
        "dst_storm_intensity",
    ]
    assert df.loc[0, "meta_window_hours"] == 12
    alerts = json.loads(df.loc[0, "alerts"])
    assert isinstance(alerts, list)


def test_persist_heliomind_dataframe_supports_parquet_json(tmp_path: Path) -> None:
    observation = _dummy_observation()
    atlas = DummyAtlas(observation)
    df = build_heliomind_dataframe(atlas=atlas)

    csv_path = tmp_path / "heliomind.csv"
    json_path = tmp_path / "heliomind.json"

    persist_heliomind_dataframe(df, csv_path)
    persist_heliomind_dataframe(df, json_path)

    assert csv_path.exists()
    assert json_path.exists()

    df_json = pd.read_json(json_path)
    assert "score" in df_json.columns
