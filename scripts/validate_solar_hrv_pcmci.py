"""Valida pipeline PCMCI+ com dados solares + HRV (WESAD + OMNI2).

LIMITAÇÃO CIENTÍFICA: WESAD contém ~2h de gravação por sujeito em condições
de laboratório. Variações HRV são dominadas pelo protocolo experimental
(~100ms RMSSD entre baseline/stress), não por atividade geomagnética (~15ms
por IQR de Kp, Ong et al. 2022). Esta execução serve para VALIDAR O PIPELINE,
NÃO para inferência causal real. Grau D.

Exemplo::

    poetry run python scripts/validate_solar_hrv_pcmci.py \\
        --omni-input data/raw/nasa_omni/omni2_hourly.parquet \\
        --hrv-input data/processed/hrv_mood_wesad.csv \\
        --tau-max 24 --alpha 0.05 --use-priors \\
        --output data/processed/causal_solar_hrv_validation.parquet
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

import pandas as pd

from darwin_heliobiology.services.causal_discovery import (
    CausalDiscoveryResult,
    build_helio_mood_priors,
    causal_results_to_dataframe,
    prepare_causal_dataframe,
    run_pcmci_plus,
)


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Valida PCMCI+ em variáveis solares + HRV (pipeline validation).",
    )
    parser.add_argument(
        "--omni-input",
        type=Path,
        default=Path("data/raw/nasa_omni/omni2_hourly.parquet"),
    )
    parser.add_argument(
        "--hrv-input",
        type=Path,
        default=Path("data/processed/hrv_mood_wesad.csv"),
    )
    parser.add_argument("--tau-max", type=int, default=24)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument(
        "--method",
        choices=["ParCorr", "CMIknn"],
        default="ParCorr",
    )
    parser.add_argument("--use-priors", action="store_true", help="Aplica priors heliobiológicos.")
    parser.add_argument(
        "--max-rows",
        type=int,
        default=2000,
        help="Máximo de linhas (default: 2000 para performance).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/causal_solar_hrv_validation.parquet"),
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    args = _parse_args(argv)
    omni_path = args.omni_input.expanduser().resolve()
    hrv_path = args.hrv_input.expanduser().resolve()

    if not omni_path.exists():
        print(f"Erro: {omni_path} não encontrado.", file=sys.stderr)
        sys.exit(1)
    if not hrv_path.exists():
        print(f"Erro: {hrv_path} não encontrado.", file=sys.stderr)
        print(
            "  Dica: rode primeiro: poetry run python scripts/ingest_wesad.py",
            file=sys.stderr,
        )
        sys.exit(1)

    print("=" * 60)
    print("PCMCI+ Solar + HRV — Validação de Pipeline (Grau D)")
    print("=" * 60)
    print(
        "AVISO: WESAD ~2h/sujeito em lab. Variações HRV dominadas pelo\n"
        "protocolo (~100ms), não por atividade geomagnética (~15ms).\n"
        "Esta execução é validação técnica, NÃO inferência causal.\n"
    )

    # Carregar dados
    print(f"Carregando OMNI2 de {omni_path} ...")
    if omni_path.suffix == ".parquet":
        omni_df = pd.read_parquet(omni_path)
    else:
        omni_df = pd.read_csv(omni_path, parse_dates=["timestamp"])

    print(f"Carregando HRV de {hrv_path} ...")
    if hrv_path.suffix == ".parquet":
        hrv_df = pd.read_parquet(hrv_path)
    else:
        hrv_df = pd.read_csv(hrv_path, parse_dates=["timestamp"])

    print(f"  OMNI2: {len(omni_df)} registros, HRV: {len(hrv_df)} registros")

    # Preparar array
    data_array, var_names = prepare_causal_dataframe(omni_df, hrv_df)

    if data_array.shape[0] > args.max_rows:
        print(f"  Limitando a {args.max_rows} linhas (de {data_array.shape[0]}).")
        data_array = data_array[-args.max_rows :]

    print(f"  Array: {data_array.shape[0]} timesteps × {data_array.shape[1]} variáveis")
    print(f"  Variáveis: {var_names}")

    # Priors
    priors = None
    if args.use_priors:
        priors = build_helio_mood_priors(var_names, args.tau_max)
        print("  Priors heliobiológicos aplicados (bio → solar bloqueado).")

    print(
        f"\nRodando PCMCI+ (tau_max={args.tau_max}, alpha={args.alpha}, method={args.method}) ..."
    )

    result: CausalDiscoveryResult = run_pcmci_plus(
        data=data_array,
        var_names=var_names,
        tau_max=args.tau_max,
        alpha=args.alpha,
        method=args.method,
        priors=priors,
    )

    print(f"\nLinks: {len(result.links)} total, {len(result.significant_links)} significativos")
    print("\n--- Links Significativos ---")
    for link in result.significant_links:
        print(
            f"  {link.source} → {link.target} "
            f"(lag={link.lag}, coeff={link.coefficient:.3f}, p={link.p_value:.4f})"
        )

    # Persistir
    output_path = args.output.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df = causal_results_to_dataframe(result)
    if output_path.suffix == ".parquet":
        df.to_parquet(output_path, index=False)
    elif output_path.suffix == ".csv":
        df.to_csv(output_path, index=False)
    else:
        df.to_json(str(output_path), orient="records", indent=2, force_ascii=False)
    print(f"\nResultados salvos em: {output_path}")


if __name__ == "__main__":
    main()
