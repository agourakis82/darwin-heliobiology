"""Testes para ingestão de dados OMNI2 hourly (NASA OMNIWeb)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from darwin_heliobiology.datasets.omni import (
    _parse_omni2_text,
    fetch_and_persist_omni,
)

# Trecho sintético no formato OMNI2 (whitespace-separated, ~55 colunas)
# Colunas relevantes (0-indexed): 0=year 1=doy 2=hour 12=bx 15=by 16=bz
#   23=density 24=speed 28=pressure 38=kp 40=dst
# Precisamos preencher 55 colunas; usamos 0 para colunas irrelevantes.
_FILLER = " ".join(["0"] * 55)


def _make_omni2_line(
    year: int = 2024,
    doy: int = 1,
    hour: int = 0,
    bx: float = -1.5,
    by: float = 2.3,
    bz: float = -4.1,
    density: float = 6.5,
    speed: float = 420.0,
    pressure: float = 2.10,
    kp: int = 27,
    dst: int = -35,
) -> str:
    """Constrói uma linha OMNI2 com os campos relevantes preenchidos."""
    cols = ["0"] * 55
    cols[0] = str(year)
    cols[1] = str(doy)
    cols[2] = str(hour)
    cols[12] = f"{bx:.1f}"
    cols[15] = f"{by:.1f}"
    cols[16] = f"{bz:.1f}"
    cols[23] = f"{density:.1f}"
    cols[24] = f"{speed:.0f}"
    cols[28] = f"{pressure:.2f}"
    cols[38] = str(kp)
    cols[40] = str(dst)
    return " ".join(cols)


SAMPLE_TEXT = "\n".join(
    [
        _make_omni2_line(year=2024, doy=1, hour=0, bx=-1.5, bz=-4.1, speed=420),
        _make_omni2_line(year=2024, doy=1, hour=1, bx=0.8, bz=2.0, speed=380),
        _make_omni2_line(year=2024, doy=1, hour=2, bx=999.9, bz=999.9, speed=9999),
    ]
)


def test_parse_omni2_text_extracts_columns() -> None:
    df = _parse_omni2_text(SAMPLE_TEXT)

    assert "timestamp" in df.columns
    assert "bx_gsm_nt" in df.columns
    assert "bz_gsm_nt" in df.columns
    assert "speed_kms" in df.columns
    assert "dst_nt" in df.columns
    assert len(df) == 3

    # Primeira linha: bz=-4.1, speed=420
    assert df.iloc[0]["bz_gsm_nt"] == pytest.approx(-4.1, abs=0.1)
    assert df.iloc[0]["speed_kms"] == pytest.approx(420.0, abs=1.0)


def test_parse_omni2_text_replaces_fill_values() -> None:
    df = _parse_omni2_text(SAMPLE_TEXT)

    # Terceira linha tem fill values (999.9, 9999)
    assert np.isnan(df.iloc[2]["bx_gsm_nt"])
    assert np.isnan(df.iloc[2]["bz_gsm_nt"])
    assert np.isnan(df.iloc[2]["speed_kms"])


def test_parse_omni2_text_builds_correct_timestamps() -> None:
    df = _parse_omni2_text(SAMPLE_TEXT)

    ts0 = df.iloc[0]["timestamp"]
    ts1 = df.iloc[1]["timestamp"]
    assert ts0.year == 2024
    assert ts0.month == 1
    assert ts0.day == 1
    assert ts0.hour == 0
    assert ts1.hour == 1


def test_fetch_and_persist_omni_writes_parquet(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "darwin_heliobiology.datasets.omni._download_omni2_year",
        lambda year, **kwargs: SAMPLE_TEXT,
    )

    result = fetch_and_persist_omni(years=[2024], output_dir=tmp_path / "omni", suffix=".parquet")

    assert result.output_path.exists()
    assert result.total_records == 3
    assert result.years == [2024]

    df = pd.read_parquet(result.output_path)
    assert "bz_gsm_nt" in df.columns


def test_fetch_and_persist_omni_csv(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "darwin_heliobiology.datasets.omni._download_omni2_year",
        lambda year, **kwargs: SAMPLE_TEXT,
    )

    result = fetch_and_persist_omni(years=[2024], output_dir=tmp_path / "omni", suffix=".csv")

    df = pd.read_csv(result.output_path)
    assert len(df) == 3
    assert "kp_index" in df.columns
