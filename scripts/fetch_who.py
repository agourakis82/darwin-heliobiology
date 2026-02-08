#!/usr/bin/env python3

"""CLI para download de dados WHO Mortality Database."""

from __future__ import annotations

import argparse
from pathlib import Path

from darwin_heliobiology.datasets.who_mortality import (
    WHO_MORTALITY_URLS,
    fetch_who_mortality,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extrai tabelas WHO mortality (CSV)")
    parser.add_argument(
        "--parts",
        nargs="+",
        choices=list(WHO_MORTALITY_URLS.keys()),
        default=None,
        help="Partes específicas para download (default: todas ICD-10)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/raw/who"),
        help="Diretório de saída (default: data/raw/who)",
    )
    parser.add_argument(
        "--skip-population",
        action="store_true",
        help="Não baixar dados de população",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Não tenta baixar (assume que CSVs já existem localmente)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.skip_download:
        print(f"Skip download. Dados esperados em {args.output_dir}")
        return

    result = fetch_who_mortality(
        parts=args.parts,
        output_dir=args.output_dir,
        include_population=not args.skip_population,
    )
    print(
        f"WHO: {len(result.files_extracted)} arquivos extraídos em "
        f"{result.output_dir} ({result.total_size_bytes / 1024 / 1024:.1f} MB)"
    )


if __name__ == "__main__":
    main()
