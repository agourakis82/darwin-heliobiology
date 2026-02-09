#!/usr/bin/env python3
"""CLI — Construção do passaporte psico-geomagnético individual."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from darwin_heliobiology.datasets.omni import _persist_df
from darwin_heliobiology.services.passport import (
    calibrate_passport,
    passport_to_dataframe,
)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Calibra passaporte psico-geomagnético a partir de dados HRV+mood e solares.",
    )
    parser.add_argument(
        "--hrv-input",
        type=Path,
        required=True,
        help="Arquivo HRV+mood (Parquet/CSV) com timestamp, hrv_rmssd, hrv_sdnn, mood_score, hr_mean.",
    )
    parser.add_argument(
        "--solar-input",
        type=Path,
        required=True,
        help="Arquivo OMNI2 ou HelioMind (Parquet/CSV) com timestamp, kp_index, dst_nt, bz_gsm_nt.",
    )
    parser.add_argument(
        "--subject-id",
        required=True,
        help="Identificador do sujeito.",
    )
    parser.add_argument(
        "--lag-max",
        type=int,
        default=72,
        help="Lag máximo em horas para correlação cruzada (default: 72).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/passport/passport.parquet"),
        help="Caminho de saída.",
    )

    args = parser.parse_args(argv)

    def _load(path: Path) -> pd.DataFrame:
        p = path.expanduser().resolve()
        if p.suffix == ".parquet":
            return pd.read_parquet(p)
        return pd.read_csv(p, parse_dates=["timestamp"])

    hrv_df = _load(args.hrv_input)
    solar_df = _load(args.solar_input)

    passport = calibrate_passport(
        subject_id=args.subject_id,
        hrv_mood_df=hrv_df,
        solar_df=solar_df,
        lag_max=args.lag_max,
    )

    out_df = passport_to_dataframe(passport)
    output_path = _persist_df(out_df, args.output)

    s = passport.sensitivity
    print(f"Passaporte: {passport.subject_id} | {passport.n_observations} observações")
    print(
        f"Sensibilidade: composta={s.composite_sensitivity:.3f} "
        f"(Kp={s.kp_coefficient:+.3f}, Dst={s.dst_coefficient:+.3f}, "
        f"Bz={s.bz_coefficient:+.3f}) | lag ótimo={s.optimal_lag_hours}h"
    )
    print(f"Storm impact: {passport.storm_impact_score:.3f}")
    if passport.vulnerable_periods:
        print(f"Períodos vulneráveis: {', '.join(passport.vulnerable_periods)}")
    print(f"Salvo em: {output_path}")


if __name__ == "__main__":
    main()
