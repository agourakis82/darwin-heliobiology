#!/usr/bin/env python3

"""CLI para download de dados OMNI2 hourly (NASA OMNIWeb)."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from darwin_heliobiology.datasets.omni import fetch_and_persist_omni


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Baixa dados OMNI2 hourly do OMNIWeb (NASA)")
    parser.add_argument(
        "--years",
        type=int,
        nargs="+",
        default=[datetime.now().year],
        help="Anos para download (default: ano atual)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/raw/nasa_omni"),
        help="Diretório de saída",
    )
    parser.add_argument(
        "--format",
        choices=["parquet", "csv", "json"],
        default="parquet",
        help="Formato de saída (default: parquet)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = fetch_and_persist_omni(
        years=args.years,
        output_dir=args.output_dir,
        suffix=f".{args.format}",
    )
    print(
        f"OMNI2: {result.total_records} registros ({result.years}) "
        f"salvos em {result.output_path}"
    )


if __name__ == "__main__":
    main()
