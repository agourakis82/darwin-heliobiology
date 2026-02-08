"""Testes para ingestão de dados WHO Mortality."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pandas as pd

from darwin_heliobiology.datasets.who_mortality import (
    _download_and_extract_zip,
    filter_suicide_mortality,
)


def _create_mock_zip(csv_content: str, filename: str = "mortality.csv") -> bytes:
    """Cria um ZIP em memória contendo um CSV."""
    buf = BytesIO()
    with ZipFile(buf, "w") as zf:
        zf.writestr(filename, csv_content)
    return buf.getvalue()


class FakeResponse:
    status_code = 200
    content: bytes

    def __init__(self, content: bytes) -> None:
        self.content = content

    def raise_for_status(self) -> None:
        pass


class FakeSession:
    def __init__(self, response: FakeResponse) -> None:
        self._response = response

    def get(self, url: str, timeout: int = 60) -> FakeResponse:
        return self._response


def test_download_and_extract_zip_creates_files(tmp_path: Path) -> None:
    csv_content = "Cause,Country,Year,Deaths\nX70,BRA,2020,150\nA01,BRA,2020,50\n"
    zip_bytes = _create_mock_zip(csv_content)
    session = FakeSession(FakeResponse(zip_bytes))

    files = _download_and_extract_zip(
        "https://example.com/fake.zip",
        tmp_path,
        session=session,  # type: ignore[arg-type]
    )

    assert len(files) == 1
    assert files[0] == "mortality.csv"
    assert (tmp_path / "mortality.csv").exists()

    df = pd.read_csv(tmp_path / "mortality.csv")
    assert len(df) == 2
    assert "Cause" in df.columns


def test_filter_suicide_mortality(tmp_path: Path) -> None:
    csv_path = tmp_path / "mortality.csv"
    csv_path.write_text(
        "Cause,Country,Year,Deaths\n"
        "X70,BRA,2020,150\n"
        "A01,BRA,2020,50\n"
        "X65,BRA,2020,80\n"
        "Y12,BRA,2020,30\n"
        "J18,BRA,2020,200\n"
    )

    df = filter_suicide_mortality(csv_path)

    assert len(df) == 3
    assert set(df["Cause"].tolist()) == {"X70", "X65", "Y12"}
