"""Testes para ingestão e cache de dados brutos NOAA SWPC."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest

from darwin_heliobiology.core.solar_atlas import SolarAtlas
from darwin_heliobiology.datasets.noaa import fetch_and_persist_noaa


def _recent(minutes: int) -> str:
    return (
        (datetime.now(tz=timezone.utc) - timedelta(minutes=minutes))
        .isoformat()
        .replace("+00:00", "Z")
    )


@pytest.fixture
def atlas(monkeypatch: pytest.MonkeyPatch) -> SolarAtlas:
    dataset = {
        "/json/planetary_k_index_1m.json": [
            {"time_tag": _recent(30), "kp": "5.0"},
            {"time_tag": _recent(60), "kp_index": "3.0"},
        ],
        "/products/kyoto-dst.json": [
            ["time_tag", "dst"],
            [_recent(30), "-45"],
            [_recent(60), "-20"],
        ],
        "/json/ace/swepam_1m.json": [
            {"time_tag": _recent(15), "speed": "420", "density": "7.5", "temperature": "150000"}
        ],
        "/json/ace/mag_1m.json": [
            {
                "time_tag": _recent(15),
                "bx_gsm": "-5",
                "by_gsm": "2",
                "bz_gsm": "-7",
                "bt": "9",
            }
        ],
    }

    instance = SolarAtlas()

    def fake_get_json(self: SolarAtlas, path: str) -> list:  # type: ignore[override]
        return dataset[path]

    monkeypatch.setattr(SolarAtlas, "_get_json", fake_get_json, raising=False)
    return instance


def test_fetch_and_persist_noaa_creates_parquet(atlas: SolarAtlas, tmp_path: Path) -> None:
    result = fetch_and_persist_noaa(
        atlas=atlas, hours=3, output_dir=tmp_path / "noaa", suffix=".parquet"
    )

    assert result.total_records > 0
    assert result.kp_path is not None and result.kp_path.exists()
    assert result.dst_path is not None and result.dst_path.exists()
    assert result.solar_wind_path is not None and result.solar_wind_path.exists()
    assert result.imf_path is not None and result.imf_path.exists()

    df_kp = pd.read_parquet(result.kp_path)
    assert "timestamp" in df_kp.columns
    assert "value" in df_kp.columns
    assert len(df_kp) == 2


def test_fetch_and_persist_noaa_creates_csv(atlas: SolarAtlas, tmp_path: Path) -> None:
    result = fetch_and_persist_noaa(
        atlas=atlas, hours=3, output_dir=tmp_path / "noaa", suffix=".csv"
    )

    assert result.kp_path is not None
    df_kp = pd.read_csv(result.kp_path)
    assert "value" in df_kp.columns
    assert "label" in df_kp.columns
