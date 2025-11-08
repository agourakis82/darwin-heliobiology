#!/usr/bin/env python3
"""Baixa, extrai e processa o dataset WESAD gerando features HRV + mood."""

from __future__ import annotations

import argparse
from pathlib import Path

from darwin_heliobiology.datasets.wesad import (
    build_wesad_hrv_mood,
    download_wesad,
    extract_wesad,
    WESAD_DOWNLOAD_URL,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingestão do dataset WESAD para HRV + mood")
    parser.add_argument(
        "--download",
        action="store_true",
        help="Força download do artefato mesmo que já exista",
    )
    parser.add_argument(
        "--url",
        default=WESAD_DOWNLOAD_URL,
        help="URL de download (padrão: link oficial WESAD)",
    )
    parser.add_argument(
        "--zip-path",
        type=Path,
        default=Path("data/raw/hrv_mood/wesad/WESAD.zip"),
        help="Local onde o ZIP será armazenado",
    )
    parser.add_argument(
        "--extract-to",
        type=Path,
        default=Path("data/raw/hrv_mood/wesad/extracted"),
        help="Diretório de extração",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/hrv_mood_wesad.csv"),
        help="Arquivo de saída (parquet/json/csv)",
    )
    parser.add_argument(
        "--window-minutes",
        type=int,
        default=5,
        help="Tamanho da janela de agregação em minutos",
    )
    parser.add_argument(
        "--min-samples",
        type=int,
        default=30,
        help="Quantidade mínima de intervalos RR por janela",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Não tenta baixar o dataset (assume que o ZIP já existe)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    zip_path = args.zip_path

    if not args.skip_download and (args.download or not zip_path.exists()):
        print(f"Baixando WESAD para {zip_path} ...")
        download_wesad(zip_path, url=args.url)

    if not zip_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {zip_path}")

    extract_dir = extract_wesad(zip_path, args.extract_to)
    result = build_wesad_hrv_mood(
        root=extract_dir,
        output_path=args.output,
        window_minutes=args.window_minutes,
        min_samples=args.min_samples,
    )

    print(f"Gerados {len(result.records)} registros HRV+mood em {result.output_path}")


if __name__ == "__main__":
    main()
