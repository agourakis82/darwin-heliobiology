from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile

import pandas as pd

from darwin_heliobiology.datasets.wesad import build_wesad_hrv_mood, extract_wesad


def _create_sample_wesad_zip(zip_path: Path) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(zip_path, "w") as archive:
        for subject in ("S2", "S3"):
            csv_path = Path(subject) / "rr.csv"
            rows = [
                {
                    "timestamp": datetime(2025, 1, 1, 8, i, tzinfo=timezone.utc).isoformat(),
                    "rr_ms": 800 + i * 5,
                    "label": "baseline" if subject == "S2" else "stress",
                }
                for i in range(10)
            ]
            content = "timestamp,rr_ms,label\n" + "\n".join(
                f"{row['timestamp']},{row['rr_ms']},{row['label']}" for row in rows
            )
            archive.writestr(str(csv_path), content)


def test_build_wesad_hrv_mood_generates_dataframe(tmp_path: Path) -> None:
    zip_path = tmp_path / "wesad.zip"
    _create_sample_wesad_zip(zip_path)
    extract_dir = extract_wesad(zip_path, tmp_path / "extracted")
    output = tmp_path / "wesad_features.csv"

    result = build_wesad_hrv_mood(
        root=extract_dir,
        output_path=output,
        window_minutes=2,
        min_samples=2,
    )

    assert output.exists()
    df = pd.read_csv(output)
    assert not df.empty
    assert set(["hrv_rmssd", "dataset", "mood_label"]).issubset(df.columns)
    assert len(result.records) == len(df)
