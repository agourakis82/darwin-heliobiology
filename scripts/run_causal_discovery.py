#!/usr/bin/env python3
"""CLI — Descoberta causal PCMCI+ entre variáveis solares e HRV/mood."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from darwin_heliobiology.datasets.omni import _persist_df
from darwin_heliobiology.services.causal_discovery import (
    build_helio_mood_priors,
    causal_results_to_dataframe,
    prepare_causal_dataframe,
    run_pcmci_plus,
)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Executa PCMCI+ para descoberta causal entre dados solares e HRV/mood.",
    )
    parser.add_argument(
        "--solar-input",
        type=Path,
        required=True,
        help="Arquivo OMNI2 ou HelioMind (Parquet/CSV).",
    )
    parser.add_argument(
        "--hrv-input",
        type=Path,
        required=True,
        help="Arquivo HRV+mood (Parquet/CSV).",
    )
    parser.add_argument("--tau-max", type=int, default=48, help="Lag máximo (default: 48).")
    parser.add_argument(
        "--alpha", type=float, default=0.05, help="Nível de significância (default: 0.05)."
    )
    parser.add_argument(
        "--method",
        choices=["ParCorr", "CMIknn"],
        default="ParCorr",
        help="Teste de independência (default: ParCorr).",
    )
    parser.add_argument(
        "--use-priors",
        action="store_true",
        help="Aplicar priors heliobiológicos de domínio.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/causal_links.parquet"),
        help="Caminho de saída.",
    )

    args = parser.parse_args(argv)

    # Carregar dados
    solar_path: Path = args.solar_input.expanduser().resolve()
    hrv_path: Path = args.hrv_input.expanduser().resolve()

    def _load(path: Path) -> pd.DataFrame:
        if path.suffix == ".parquet":
            return pd.read_parquet(path)
        return pd.read_csv(path, parse_dates=["timestamp"])

    solar_df = _load(solar_path)
    hrv_df = _load(hrv_path)

    data, var_names = prepare_causal_dataframe(solar_df, hrv_df)

    priors = build_helio_mood_priors(var_names, tau_max=args.tau_max) if args.use_priors else None

    result = run_pcmci_plus(
        data,
        var_names,
        tau_max=args.tau_max,
        alpha=args.alpha,
        method=args.method,
        priors=priors,
    )

    out_df = causal_results_to_dataframe(result)
    output_path = _persist_df(out_df, args.output)

    print(
        f"PCMCI+ ({args.method}): {len(result.links)} links, "
        f"{len(result.significant_links)} significativos (α={args.alpha})"
    )
    print(f"Salvo em: {output_path}")


if __name__ == "__main__":
    main()
