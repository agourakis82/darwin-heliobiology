"""Valida pipeline PCMCI+ em variáveis solares (sem HRV).

Roda causal discovery em dados OMNI2 puros para confirmar links físicos conhecidos
(e.g., Bz → Dst, autocorrelação Kp).

Exemplo::

    poetry run python scripts/validate_solar_pcmci.py \\
        --omni-input data/raw/nasa_omni/omni2_hourly.parquet \\
        --tau-max 24 --alpha 0.05 \\
        --output data/processed/causal_solar_validation.parquet
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

import pandas as pd

from darwin_heliobiology.pipelines.calibration import prepare_solar_only_dataframe
from darwin_heliobiology.services.causal_discovery import (
    CausalDiscoveryResult,
    causal_results_to_dataframe,
    run_pcmci_plus,
)


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Valida PCMCI+ em variáveis solares (sem HRV).",
    )
    parser.add_argument(
        "--omni-input",
        type=Path,
        default=Path("data/raw/nasa_omni/omni2_hourly.parquet"),
        help="Caminho do arquivo OMNI2.",
    )
    parser.add_argument("--tau-max", type=int, default=24, help="Lag máximo em horas.")
    parser.add_argument("--alpha", type=float, default=0.05, help="Nível de significância.")
    parser.add_argument(
        "--method",
        choices=["ParCorr", "CMIknn"],
        default="ParCorr",
        help="Teste de independência.",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=8760,
        help="Máximo de linhas para evitar lentidão (default: 1 ano = 8760).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/causal_solar_validation.parquet"),
        help="Caminho de saída.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    args = _parse_args(argv)
    omni_path = args.omni_input.expanduser().resolve()

    if not omni_path.exists():
        print(f"Erro: arquivo não encontrado: {omni_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Carregando dados OMNI2 de {omni_path} ...")
    if omni_path.suffix == ".parquet":
        omni_df = pd.read_parquet(omni_path)
    else:
        omni_df = pd.read_csv(omni_path, parse_dates=["timestamp"])

    # Limitar número de linhas para performance
    if len(omni_df) > args.max_rows:
        print(f"  Limitando a {args.max_rows} linhas (de {len(omni_df)}).")
        omni_df = omni_df.tail(args.max_rows).reset_index(drop=True)

    data_array, var_names = prepare_solar_only_dataframe(omni_df)
    print(f"  Array: {data_array.shape[0]} timesteps × {data_array.shape[1]} variáveis")
    print(f"  Variáveis: {var_names}")
    print(f"  tau_max={args.tau_max}, alpha={args.alpha}, method={args.method}")

    print("\nRodando PCMCI+ ... (pode levar alguns minutos)")
    result: CausalDiscoveryResult = run_pcmci_plus(
        data=data_array,
        var_names=var_names,
        tau_max=args.tau_max,
        alpha=args.alpha,
        method=args.method,
    )

    print(
        f"\nLinks descobertos: {len(result.links)} total, {len(result.significant_links)} significativos"
    )
    print("\n--- Links Significativos ---")
    for link in result.significant_links:
        print(
            f"  {link.source} → {link.target} (lag={link.lag}, coeff={link.coefficient:.3f}, p={link.p_value:.4f})"
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
