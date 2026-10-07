"""Migra um parquet OMNI2 legado (Kp ×10) para a escala real 0–9. Idempotente."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from darwin_heliobiology.datasets.omni import ensure_kp_scale


def main(path: Path) -> int:
    df = pd.read_parquet(path)
    before = float(df["kp_index"].max())
    df["kp_index"] = ensure_kp_scale(df["kp_index"])
    df.to_parquet(path, index=False)
    print(f"{path}: Kp max {before} -> {float(df['kp_index'].max())} ({len(df)} registros)")
    return 0


if __name__ == "__main__":
    sys.exit(
        main(Path(sys.argv[1] if len(sys.argv) > 1 else "data/raw/nasa_omni/omni2_hourly.parquet"))
    )
