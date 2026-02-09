#!/usr/bin/env python3
"""CLI — Construção do atlas temporal de assinaturas geomagnéticas."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from darwin_heliobiology.core.geomagnetic_atlas import (
    atlas_to_dataframe,
    build_geomagnetic_atlas,
)
from darwin_heliobiology.datasets.omni import _persist_df


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Constrói atlas temporal de assinaturas geomagnéticas a partir de dados OMNI2.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Caminho para arquivo OMNI2 (Parquet ou CSV).",
    )
    parser.add_argument(
        "--resolution",
        choices=["daily", "monthly", "quarterly"],
        default="monthly",
        help="Resolução temporal (default: monthly).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/geomagnetic_atlas.parquet"),
        help="Caminho de saída.",
    )

    args = parser.parse_args(argv)

    input_path: Path = args.input.expanduser().resolve()
    if input_path.suffix == ".parquet":
        df = pd.read_parquet(input_path)
    elif input_path.suffix == ".csv":
        df = pd.read_csv(input_path, parse_dates=["timestamp"])
    else:
        raise ValueError(f"Formato de entrada não suportado: {input_path.suffix}")

    result = build_geomagnetic_atlas(df, resolution=args.resolution)
    out_df = atlas_to_dataframe(result)
    output_path = _persist_df(out_df, args.output)

    print(
        f"Atlas geomagnético: {len(result.signatures)} períodos "
        f"({result.resolution}), anos {result.year_range[0]}-{result.year_range[1]}"
    )
    print(f"Salvo em: {output_path}")


if __name__ == "__main__":
    main()
