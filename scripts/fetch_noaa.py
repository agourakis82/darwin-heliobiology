#!/usr/bin/env python3

"""CLI para download e cache de índices NOAA SWPC (Kp, Dst, Bz, vento solar)."""

from __future__ import annotations

import argparse
from pathlib import Path

from darwin_heliobiology.core.solar_atlas import SolarAtlas
from darwin_heliobiology.datasets.noaa import fetch_and_persist_noaa


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Baixa e cacheia índices Kp/Dst/Bz da NOAA SWPC")
    parser.add_argument(
        "--hours",
        type=int,
        default=24,
        help="Janela de horas para ingestão (default: 24)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/raw/noaa"),
        help="Diretório de saída para dados brutos",
    )
    parser.add_argument(
        "--format",
        choices=["parquet", "csv", "json"],
        default="parquet",
        help="Formato de saída (default: parquet)",
    )
    parser.add_argument(
        "--base-url",
        default="https://services.swpc.noaa.gov",
        help="Endpoint base da NOAA SWPC",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Imprime resumo sem salvar",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    atlas = SolarAtlas(base_url=args.base_url)

    if args.dry_run:
        obs = atlas.snapshot(hours=args.hours)
        print(f"Kp: {len(obs.kp_series)} registros")
        print(f"Dst: {len(obs.dst_series)} registros")
        print(f"Solar wind: {len(obs.solar_wind)} registros")
        print(f"IMF: {len(obs.imf)} registros")
        return

    result = fetch_and_persist_noaa(
        atlas=atlas,
        hours=args.hours,
        output_dir=args.output_dir,
        suffix=f".{args.format}",
    )
    print(f"NOAA: {result.total_records} registros salvos em {args.output_dir}")


if __name__ == "__main__":
    main()
