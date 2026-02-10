"""Calibra pesos do HelioMind Index via regressão sobre mortalidade WHO.

Exemplo::

    poetry run python scripts/calibrate_who_weights.py \\
        --who-dir data/raw/who \\
        --omni-input data/raw/nasa_omni/omni2_hourly.parquet \\
        --outcome suicide cardiovascular \\
        --output data/processed/calibrated_weights.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

import pandas as pd

from darwin_heliobiology.pipelines.who_calibration import (
    WHOCalibrationConfig,
    calibrated_weights_to_json,
    derive_weights_from_betas,
    prepare_who_solar_panel,
    run_panel_regression,
)

# ICD-10 prefixes por outcome
OUTCOME_ICD10: dict[str, list[str]] = {
    "suicide": [f"X{i}" for i in range(60, 85)] + [f"Y{i}" for i in range(10, 35)],
    "cardiovascular": [f"I{i:02d}" for i in range(0, 100)],
}


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Calibra pesos do HelioMind Index via mortalidade WHO.",
    )
    parser.add_argument(
        "--who-dir",
        type=Path,
        default=Path("data/raw/who"),
    )
    parser.add_argument(
        "--omni-input",
        type=Path,
        default=Path("data/raw/nasa_omni/omni2_hourly.parquet"),
    )
    parser.add_argument(
        "--outcome",
        nargs="+",
        default=["suicide", "cardiovascular"],
        help="Outcomes para regressão.",
    )
    parser.add_argument("--min-year", type=int, default=2000)
    parser.add_argument("--max-year", type=int, default=2022)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/calibrated_weights.json"),
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    args = _parse_args(argv)
    who_dir = args.who_dir.expanduser().resolve()
    omni_path = args.omni_input.expanduser().resolve()

    if not who_dir.exists():
        print(f"Erro: {who_dir} não encontrado.", file=sys.stderr)
        print("  Dica: rode primeiro: poetry run python scripts/fetch_who.py", file=sys.stderr)
        sys.exit(1)
    if not omni_path.exists():
        print(f"Erro: {omni_path} não encontrado.", file=sys.stderr)
        sys.exit(1)

    print("=" * 60)
    print("WHO Weight Calibration — HelioMind Index")
    print("=" * 60)
    print(f"  WHO dir: {who_dir}")
    print(f"  OMNI2: {omni_path}")
    print(f"  Outcomes: {args.outcome}")
    print(f"  Anos: {args.min_year}–{args.max_year}\n")

    # Carregar OMNI2
    if omni_path.suffix == ".parquet":
        omni_df = pd.read_parquet(omni_path)
    else:
        omni_df = pd.read_csv(omni_path, parse_dates=["timestamp"])

    results = []
    for outcome in args.outcome:
        print(f"\n--- Outcome: {outcome} ---")
        config = WHOCalibrationConfig(
            outcome=outcome,
            icd10_prefixes=OUTCOME_ICD10.get(outcome, []),
            min_year=args.min_year,
            max_year=args.max_year,
        )
        panel = prepare_who_solar_panel(who_dir, omni_df, config)
        if panel.empty:
            print(f"  Painel vazio para {outcome}. Pulando.")
            continue

        print(f"  Painel: {len(panel)} observações (país × ano)")
        result = run_panel_regression(panel, config)
        results.append(result)

        print(f"  R²: {result.r_squared:.4f}")
        for comp, coeff in result.coefficients.items():
            p = result.p_values.get(comp, float("nan"))
            print(f"    {comp}: β={coeff:.4f}, p={p:.4f}")

    if not results:
        print("\nNenhum resultado de regressão. Abortando.", file=sys.stderr)
        sys.exit(1)

    calibrated = derive_weights_from_betas(results)
    print(f"\n{'=' * 60}")
    print("Pesos Calibrados (Grau C)")
    print(f"{'=' * 60}")
    for comp, w in calibrated.weights.items():
        print(f"  {comp}: {w:.4f}")
    print(f"  Soma: {sum(calibrated.weights.values()):.4f}")

    output_path = args.output.expanduser().resolve()
    calibrated_weights_to_json(calibrated, output_path)
    print(f"\nResultados salvos em: {output_path}")


if __name__ == "__main__":
    main()
