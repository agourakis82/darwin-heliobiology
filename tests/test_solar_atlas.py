"""Testes para ingestão pública de dados solares."""

from datetime import datetime, timedelta, timezone

import pytest

from darwin_heliobiology.core.solar_atlas import SolarAtlas


def _recent(minutes: int) -> str:
    return (
        (datetime.now(tz=timezone.utc) - timedelta(minutes=minutes))
        .isoformat()
        .replace("+00:00", "Z")
    )


@pytest.fixture
def atlas(monkeypatch):
    dataset = {
        "/json/planetary_k_index_1m.json": [
            {"time_tag": _recent(30), "kp": "5.0"},
            {"time_tag": _recent(120), "kp_index": "3.0"},
        ],
        "/products/kyoto-dst.json": [
            ["time_tag", "dst"],
            [_recent(30), "-45"],
            [_recent(180), "-20"],
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

    def fake_get_json(self, path):
        return dataset[path]

    monkeypatch.setattr(SolarAtlas, "_get_json", fake_get_json, raising=False)
    return instance


def test_snapshot_returns_structured_observation(atlas):
    observation = atlas.snapshot(hours=3)

    assert len(observation.kp_series) == 2  # 2 datapoints acima do cutoff
    assert observation.kp_series[0].label == "Kp"
    assert observation.dst_series[0].label == "Dst"
    assert observation.solar_wind[0].speed_kms == 420.0
    assert observation.imf[0].bz_nt == -7.0
    assert observation.metadata["source"] == "NOAA SWPC"


def test_fetch_kp_index_filters_by_hours(atlas):
    series = atlas.fetch_kp_index(hours=1)
    assert len(series) == 1
    assert series[0].value == 5.0
