#!/usr/bin/env python3

"""CLI para construção do HelioMind Index com dados públicos da NOAA."""

from __future__ import annotations

import argparse
from pathlib import Path

from darwin_heliobiology.core.solar_atlas import SolarAtlas
from darwin_heliobiology.pipelines.heliomind_builder import (
    build_heliomind_dataframe,
    persist_heliomind_dataframe,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gera o HelioMind Index a partir da NOAA SWPC")
    parser.add_argument(
        "--hours",
        type=int,
        default=24,
        help="Janela de horas para ingestão (default: 24)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/heliomind_index.parquet"),
        help="Arquivo de saída (.parquet, .json, .ndjson ou .csv)",
    )
    parser.add_argument(
        "--base-url",
        default="https://services.swpc.noaa.gov",
        help="Endpoint base da NOAA SWPC",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Apenas imprime o resultado em stdout, sem salvar arquivo",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    atlas = SolarAtlas(base_url=args.base_url)
    df = build_heliomind_dataframe(atlas=atlas, hours=args.hours)

    if args.dry_run:
        print(df.to_markdown(index=False))
        return

    output_path = persist_heliomind_dataframe(df, args.output)
    print(f"HelioMind Index salvo em {output_path}")


if __name__ == "__main__":
    main()
