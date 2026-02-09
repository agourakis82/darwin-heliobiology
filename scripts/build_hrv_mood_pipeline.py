#!/usr/bin/env python3

"""CLI genérico para produzir features HRV + mood a partir de qualquer CSV com RR intervals."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, Sequence

import pandas as pd

from darwin_heliobiology.pipelines.hrv_mood import (
    build_hrv_mood_records,
    records_to_dataframe,
)

DEFAULT_SCALES: Dict[str, Sequence[float]] = {"mood": (0.0, 1.0)}
DEFAULT_RESPONSES: Dict[str, float] = {"mood": 0.5}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gera features HRV + mood a partir de CSV com colunas timestamp e rr_ms"
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="CSV de entrada (colunas: timestamp, rr_ms; opcionais: mood_score, label)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/hrv_mood_features.parquet"),
        help="Arquivo de saída (.parquet, .json ou .csv)",
    )
    parser.add_argument(
        "--window-minutes",
        type=int,
        default=5,
        help="Tamanho da janela de agregação em minutos (default: 5)",
    )
    parser.add_argument(
        "--min-samples",
        type=int,
        default=30,
        help="Quantidade mínima de intervalos RR por janela (default: 30)",
    )
    parser.add_argument(
        "--dataset",
        default="generic",
        help="Rótulo do dataset de origem (default: generic)",
    )
    parser.add_argument(
        "--subject-id",
        default=None,
        help="Identificador do sujeito (default: derivado do nome do arquivo)",
    )
    return parser.parse_args()


def _resolve_mood(df: pd.DataFrame) -> Dict[str, float]:
    """Determina resposta de humor a partir das colunas disponíveis."""
    if "mood_score" in df.columns:
        score = float(df["mood_score"].mean())
        return {"mood": score}
    return DEFAULT_RESPONSES


def main() -> None:
    args = parse_args()
    input_path: Path = args.input

    if not input_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {input_path}")

    df = pd.read_csv(input_path)
    if "timestamp" not in df.columns or "rr_ms" not in df.columns:
        raise ValueError("CSV precisa conter colunas 'timestamp' e 'rr_ms'")

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    subject_id = args.subject_id or input_path.stem
    mood_responses = _resolve_mood(df)

    records = build_hrv_mood_records(
        subject_id=subject_id,
        dataset=args.dataset,
        rr_intervals_ms=df["rr_ms"].astype(float).tolist(),
        mood_responses=mood_responses,
        scales=DEFAULT_SCALES,
        timestamps=df["timestamp"].tolist(),
        window_minutes=args.window_minutes,
        min_samples=args.min_samples,
    )

    out_df = records_to_dataframe(records)

    output_path = args.output.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.suffix == ".parquet":
        out_df.to_parquet(output_path, index=False)
    elif output_path.suffix == ".json":
        out_df.to_json(str(output_path), orient="records", force_ascii=False, indent=2)
    else:
        out_df.to_csv(output_path, index=False)

    print(f"Gerados {len(records)} registros HRV+mood em {output_path}")


if __name__ == "__main__":
    main()
