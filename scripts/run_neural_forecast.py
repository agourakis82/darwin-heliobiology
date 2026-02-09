#!/usr/bin/env python3
"""CLI — Pipeline de previsão TFT/PatchTST com features HelioMind + HRV."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from darwin_heliobiology.datasets.omni import _persist_df
from darwin_heliobiology.pipelines.neural_forecast import (
    NeuralForecastConfig,
    prepare_neuralforecast_df,
    train_and_forecast,
)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Treina TFT ou PatchTST com dados solares + HRV e gera previsões.",
    )
    parser.add_argument(
        "--solar-input",
        type=Path,
        required=True,
        help="Dados solares OMNI2 ou HelioMind (Parquet/CSV).",
    )
    parser.add_argument(
        "--hrv-input",
        type=Path,
        default=None,
        help="Dados HRV+mood opcionais (Parquet/CSV).",
    )
    parser.add_argument(
        "--model",
        choices=["tft", "patchtst"],
        default="tft",
        help="Modelo a usar (default: tft).",
    )
    parser.add_argument("--horizon", type=int, default=24, help="Passos de previsão (default: 24).")
    parser.add_argument(
        "--input-size", type=int, default=168, help="Janela de lookback (default: 168)."
    )
    parser.add_argument(
        "--max-steps", type=int, default=500, help="Iterações de treino (default: 500)."
    )
    parser.add_argument(
        "--target",
        default="kp_index",
        help="Coluna alvo para previsão (default: kp_index).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/neural_forecast.parquet"),
        help="Caminho de saída.",
    )

    args = parser.parse_args(argv)

    def _load(path: Path) -> pd.DataFrame:
        p = path.expanduser().resolve()
        if p.suffix == ".parquet":
            return pd.read_parquet(p)
        return pd.read_csv(p, parse_dates=["timestamp"])

    solar_df = _load(args.solar_input)
    hrv_df = _load(args.hrv_input) if args.hrv_input else None

    config = NeuralForecastConfig(
        model_type=args.model,
        horizon=args.horizon,
        input_size=args.input_size,
        max_steps=args.max_steps,
        target_col=args.target,
    )

    nf_df = prepare_neuralforecast_df(solar_df, hrv_df, target_col=args.target)

    result = train_and_forecast(nf_df, config)
    output_path = _persist_df(result.predictions, args.output)

    print(f"Modelo: {result.model_type} | Horizonte: {config.horizon}h")
    if result.metrics:
        metrics_str = ", ".join(f"{k}={v:.4f}" for k, v in result.metrics.items())
        print(f"Métricas: {metrics_str}")
    print(f"Previsões salvas em: {output_path}")


if __name__ == "__main__":
    main()
