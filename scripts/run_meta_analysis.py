"""Roda metaanálises DerSimonian-Laird por domínio heliobiológico.

Exemplo::

    poetry run python scripts/run_meta_analysis.py \
        --domains cardiovascular hrv suicide \
        --output data/processed/meta_analysis_results.parquet
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from darwin_heliobiology.pipelines.meta_analysis_runner import (
    meta_results_to_dataframe,
    print_meta_summary,
    run_domain_meta_analyses,
)


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Roda metaanálises por domínio heliobiológico.",
    )
    parser.add_argument(
        "--domains",
        nargs="+",
        default=["cardiovascular", "hrv", "suicide"],
        help="Domínios para análise (default: todos).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/meta_analysis_results.parquet"),
        help="Caminho de saída.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Apenas imprime resumo (não salva arquivo).",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    args = _parse_args(argv)

    print(f"Rodando metaanálises para domínios: {args.domains}")
    results = run_domain_meta_analyses(args.domains)

    if not results:
        print("Nenhum domínio com estudos suficientes para metaanálise.", file=sys.stderr)
        sys.exit(1)

    print_meta_summary(results)

    if args.dry_run:
        return

    output_path = args.output.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df = meta_results_to_dataframe(results)
    if output_path.suffix == ".parquet":
        df.to_parquet(output_path, index=False)
    elif output_path.suffix == ".csv":
        df.to_csv(output_path, index=False)
    else:
        df.to_json(str(output_path), orient="records", indent=2, force_ascii=False)
    print(f"Resultados salvos em: {output_path}")


if __name__ == "__main__":
    main()
