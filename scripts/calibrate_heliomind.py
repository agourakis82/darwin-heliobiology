"""Calibra constantes do HelioMind Index contra dados OMNI2 reais.

Exemplo::

    poetry run python scripts/calibrate_heliomind.py \\
        --omni-input data/raw/nasa_omni/omni2_hourly.parquet \\
        --output data/processed/calibration_report.parquet \\
        --apply
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import pandas as pd

from darwin_heliobiology.pipelines.calibration import (
    build_calibration_report,
    calibration_report_to_dataframe,
    print_calibration_summary,
)


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Calibra HelioMind Index contra dados OMNI2.",
    )
    parser.add_argument(
        "--omni-input",
        type=Path,
        default=Path("data/raw/nasa_omni/omni2_hourly.parquet"),
        help="Caminho do arquivo OMNI2 (parquet ou CSV).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/calibration_report.parquet"),
        help="Caminho de saída do relatório.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Salva calibration_constants.json junto ao output.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Apenas imprime resumo (não salva arquivos).",
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

    print(f"  {len(omni_df)} registros carregados.")
    report = build_calibration_report(omni_df)
    print_calibration_summary(report)

    if args.dry_run:
        return

    output_path = args.output.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df = calibration_report_to_dataframe(report)
    if output_path.suffix == ".parquet":
        df.to_parquet(output_path, index=False)
    elif output_path.suffix == ".csv":
        df.to_csv(output_path, index=False)
    else:
        df.to_json(str(output_path), orient="records", indent=2, force_ascii=False)
    print(f"Relatório salvo em: {output_path}")

    if args.apply:
        constants = {
            "calibrated_from": f"OMNI2 {report.years[0]}-{report.years[-1]}",
            "n_records": report.n_records,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "constants": {},
        }
        for d in report.distributions:
            key = d.variable.replace("_gsm", "").replace("_12h", "")
            constants["constants"][key] = {
                "current": d.current_divisor,
                "calibrated_p99": d.suggested_divisor,
            }
        json_path = output_path.parent / "calibration_constants.json"
        json_path.write_text(json.dumps(constants, indent=2, ensure_ascii=False))
        print(f"Constantes salvas em: {json_path}")


if __name__ == "__main__":
    main()
