"""Reconstrói arquivos OMNI2 (.dat, formato de texto da NASA) a partir do parquet versionado.

POR QUE EXISTE: ``spdf.gsfc.nasa.gov`` não é alcançável da máquina de desenvolvimento
(timeout de conexão IPv4/IPv6, medido em 2026-10-06; `scripts/collect_raw.sh omni2` é o
caminho preferido e deve ser usado onde houver rota). Este script NÃO é a fonte da
verdade: é a mesma série (52 608 horas, 2020-2025) re-serializada no layout OMNI2
(55 colunas, Kp ×10, fills 999.9/9999./99.99/99/99999), para que o parser Sounio seja
exercitado em dados do tamanho real. As colunas não usadas saem com fill.

Só conversão de formato; nenhum valor é calculado.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd

OUT = Path("data/raw/omni2")


def _f(v: float, width: int, dec: int, fill: str) -> str:
    return (
        fill.rjust(width)
        if v is None or (isinstance(v, float) and math.isnan(v))
        else f"{v:{width}.{dec}f}"
    )


def line(r: pd.Series) -> str:
    ts = pd.Timestamp(r["timestamp"])
    kp10 = None if pd.isna(r["kp_index"]) else int(round(r["kp_index"] * 10))
    dst = None if pd.isna(r["dst_nt"]) else int(round(r["dst_nt"]))
    spd = None if pd.isna(r["speed_kms"]) else float(r["speed_kms"])
    parts = [
        f"{ts.year:4d}",
        f"{ts.dayofyear:4d}",
        f"{ts.hour:3d}",
        f"{1771:5d}",
        "99".rjust(3),
        "99".rjust(3),
        "999".rjust(4),
        "999".rjust(4),
        "999.9".rjust(6),
        "999.9".rjust(6),
        "999.9".rjust(6),
        "999.9".rjust(6),  # 8..11
        _f(r["bx_gsm_nt"], 6, 1, "999.9"),  # 12 Bx
        "999.9".rjust(6),  # 13 By GSE
        "999.9".rjust(6),  # 14 Bz GSE
        _f(r["by_gsm_nt"], 6, 1, "999.9"),  # 15
        _f(r["bz_gsm_nt"], 6, 1, "999.9"),  # 16
        *["999.9".rjust(6)] * 5,  # 17..21
        "9999999.".rjust(9),  # 22 T
        _f(r["proton_density_pcm3"], 6, 1, "999.9"),  # 23
        ("9999." if spd is None else f"{spd:.0f}.").rjust(6),  # 24
        "999.9".rjust(6),
        "999.9".rjust(6),
        "9.999".rjust(6),  # 25..27
        _f(r["flow_pressure_npa"], 6, 2, "99.99"),  # 28
        "9999999.".rjust(9),
        "999.9".rjust(6),
        "9999.".rjust(6),
        "999.9".rjust(6),
        "999.9".rjust(6),
        "9.999".rjust(6),
        "999.99".rjust(7),
        "999.99".rjust(7),
        "99.9".rjust(6),  # 29..37
        ("99" if kp10 is None else str(kp10)).rjust(3),  # 38 Kp*10
        "999".rjust(4),  # 39 R
        ("99999" if dst is None else str(dst)).rjust(6),  # 40 Dst
        "9999".rjust(5),
        "999999.99".rjust(10),
        *["99999.99".rjust(9)] * 5,  # 41..47
        "0".rjust(3),
        "999".rjust(4),
        "999.9".rjust(6),
        "999.9".rjust(6),  # 48..51
        "99999".rjust(6),
        "99999".rjust(6),
        "999.9".rjust(5),  # 52..54
    ]
    assert len(parts) == 55, len(parts)
    return " ".join(p.strip() if False else p for p in parts)


def main(src: Path) -> int:
    df = pd.read_parquet(src)
    OUT.mkdir(parents=True, exist_ok=True)
    for year, g in df.groupby(pd.to_datetime(df["timestamp"]).dt.year):
        path = OUT / f"omni2_{year}.dat"
        path.write_text("\n".join(line(r) for _, r in g.iterrows()) + "\n")
        print(f"{path}: {len(g)} linhas")
    return 0


if __name__ == "__main__":
    sys.exit(
        main(Path(sys.argv[1] if len(sys.argv) > 1 else "data/raw/nasa_omni/omni2_hourly.parquet"))
    )
