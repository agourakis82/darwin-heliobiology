"""Benchmark de modelos de previsão: Kairos vs TFT vs PatchTST.

Exemplo::

    poetry run python scripts/benchmark_forecasters.py \\
        --omni-input data/raw/nasa_omni/omni2_hourly.parquet \\
        --horizon 24 --max-steps 500 \\
        --output data/processed/forecast_benchmark.parquet
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

import pandas as pd

from darwin_heliobiology.pipelines.forecast_benchmark import (
    benchmark_to_dataframe,
    print_benchmark_summary,
    run_benchmark,
)


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark de previsão: Kairos vs TFT vs PatchTST.",
    )
    parser.add_argument(
        "--omni-input",
        type=Path,
        default=Path("data/raw/nasa_omni/omni2_hourly.parquet"),
    )
    parser.add_argument("--horizon", type=int, default=24)
    parser.add_argument("--max-steps", type=int, default=500)
    parser.add_argument(
        "--max-rows",
        type=int,
        default=0,
        help="Limitar registros para performance (0 = sem limite).",
    )
    parser.add_argument("--target", default="kp_index", help="Coluna alvo.")
    parser.add_argument(
        "--models",
        nargs="+",
        default=["kairos", "tft", "patchtst"],
        help="Modelos a rodar.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/forecast_benchmark.parquet"),
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    args = _parse_args(argv)
    omni_path = args.omni_input.expanduser().resolve()

    if not omni_path.exists():
        print(f"Erro: {omni_path} não encontrado.", file=sys.stderr)
        sys.exit(1)

    print(f"Carregando OMNI2 de {omni_path} ...")
    if omni_path.suffix == ".parquet":
        omni_df = pd.read_parquet(omni_path)
    else:
        omni_df = pd.read_csv(omni_path, parse_dates=["timestamp"])

    if args.max_rows > 0 and len(omni_df) > args.max_rows:
        print(f"  Limitando a {args.max_rows} linhas (de {len(omni_df)}).")
        omni_df = omni_df.tail(args.max_rows).reset_index(drop=True)

    print(f"  {len(omni_df)} registros, modelos: {args.models}")
    print(f"  horizon={args.horizon}, max_steps={args.max_steps}, target={args.target}\n")

    results = run_benchmark(
        omni_df,
        horizon=args.horizon,
        max_steps=args.max_steps,
        target_col=args.target,
        models=args.models,
    )

    print_benchmark_summary(results)

    output_path = args.output.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df = benchmark_to_dataframe(results)
    if output_path.suffix == ".parquet":
        df.to_parquet(output_path, index=False)
    elif output_path.suffix == ".csv":
        df.to_csv(output_path, index=False)
    else:
        df.to_json(str(output_path), orient="records", indent=2, force_ascii=False)
    print(f"Resultados salvos em: {output_path}")


if __name__ == "__main__":
    main()
