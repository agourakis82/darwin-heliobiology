"""Corroboração Python (ADR-008/ADR-009: `external_corroboration_only`).

Roda a versão Python (já corrigida em fix/data-integrity) sobre AS MESMAS entradas do gate e
REPORTA divergências contra a saída do núcleo Sounio numa tabela. NUNCA é juiz: o código de
saída é sempre 0 e nada aqui entra no veredito de `make sio-test`.

Uso (a partir da raiz, depois de `make sio-twin`):  python tests/corroboration/run.py
Lê:   build/gate/twin_main.out (saída do núcleo Sounio sobre gate/cmds_*.txt)
Grava: build/corroboration/report.md
"""

from __future__ import annotations

import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from darwin_heliobiology.core.geomagnetic_atlas import (
    build_geomagnetic_atlas,
)
from darwin_heliobiology.datasets.omni import _parse_omni2_text
from darwin_heliobiology.metrics.helio_index import (
    compute_helio_mind_index,
)
from darwin_heliobiology.models.solar import (
    IMFVector,
    SolarIndex,
    SolarObservation,
    SolarWindSample,
)
from darwin_heliobiology.pipelines.calibration import (
    compute_empirical_distributions,
)
from darwin_heliobiology.services.aletheia_validator import (
    AletheiaValidator,
    StudyEffect,
)
from darwin_heliobiology.services.passport import _cross_correlate_at_lags

TOKEN = re.compile(r"^([+-])(\d+)p([+-]\d+)$")


def tok(s: str) -> float | None:
    """Decodifica o token numérico exato do protocolo (spec §0.1). `NA` -> None."""
    if s == "NA":
        return None
    if s == "0":
        return 0.0
    if s in ("nan",):
        return math.nan
    if s in ("+inf", "-inf"):
        return math.inf if s[0] == "+" else -math.inf
    m = TOKEN.match(s)
    if m:
        v = math.ldexp(int(m.group(2)), int(m.group(3)) - 52)
        return -v if m.group(1) == "-" else v
    return float(s)


def read_blocks(path: Path) -> Dict[str, List[List[str]]]:
    blocks: Dict[str, List[List[str]]] = {}
    cur = None
    for line in path.read_text().splitlines():
        if line.startswith("begin "):
            cur = line[6:].strip()
            blocks[cur] = []
        elif line.strip() == "end":
            cur = None
        elif cur is not None and line.strip():
            blocks[cur].append(line.split())
    return blocks


ROWS: List[Tuple[str, str, str, str, str, str]] = []  # case, quantity, sounio, python, rel, status


def rel(a: float | None, b: float | None) -> float:
    if a is None and b is None:
        return 0.0
    if a is None or b is None:
        return math.inf
    if math.isnan(a) and math.isnan(b):
        return 0.0
    if a == b:
        return 0.0
    return abs(a - b) / max(abs(a), abs(b), 1e-6)


def add(case: str, q: str, s: float | None, p: float | None, tol: float = 1e-9) -> None:
    r = rel(s, p)
    status = "ok" if r <= tol else "DIVERGE"
    f = lambda x: "NA" if x is None else (f"{x:.12g}")
    ROWS.append((case, q, f(s), f(p), f"{r:.2e}" if math.isfinite(r) else "inf", status))


def addi(case: str, q: str, s: int, p: int) -> None:
    ROWS.append((case, q, str(s), str(p), "0" if s == p else "int", "ok" if s == p else "DIVERGE"))


# ---------------------------------------------------------------- helio ----------------------
def helio_case(path: Path) -> SolarObservation:
    now = 0
    kp: List[SolarIndex] = []
    dst: List[SolarIndex] = []
    imf: List[IMFVector] = []
    wind: List[SolarWindSample] = []

    def ts(sec: int) -> datetime:
        return datetime.fromtimestamp(sec, tz=timezone.utc)

    def val(s: str) -> float:
        return math.nan if s == "NA" else float(s)

    for line in path.read_text().splitlines():
        t = line.split("#")[0].split()
        if not t:
            continue
        if t[0] == "NOW":
            now = int(t[1])
        elif t[0] == "KP":
            kp.append(SolarIndex(ts(int(t[1])), val(t[2]), "Kp"))
        elif t[0] == "DST":
            dst.append(SolarIndex(ts(int(t[1])), val(t[2]), "Dst"))
        elif t[0] == "BZ":
            imf.append(IMFVector(ts(int(t[1])), 0.0, 0.0, val(t[2]), 0.0))
        elif t[0] == "WIND":
            wind.append(SolarWindSample(ts(int(t[1])), val(t[3]), val(t[2]), 1e5))
    return SolarObservation(kp, dst, wind, imf, {"now": now})


ALERT_BITS = [
    ("Kp elevado", 1),
    ("Dst muito", 2),
    ("Bz sul", 4),
    ("Pressao", 8),
    ("Variabilidade", 16),
]


def helio(blocks: Dict[str, List[List[str]]]) -> None:
    for header, lines in blocks.items():
        if not header.startswith("helio "):
            continue
        path = ROOT / header.split()[1]
        case = f"helio {path.name}"
        r = compute_helio_mind_index(helio_case(path))
        got = {
            (l[0] + " " + l[1] if l[0] == "comp" else l[0]): (l[2:] if l[0] == "comp" else l[1:])
            for l in lines
        }
        comps = [
            ("kp", r.components.kp_activity),
            ("dst", r.components.dst_storm_intensity),
            ("bz", r.components.bz_reconnection),
            ("pressure", r.components.solar_wind_pressure),
            ("variability", r.components.variability),
        ]
        for name, v in comps:
            add(
                case,
                f"comp {name}",
                tok(got[f"comp {name}"][0]),
                None if math.isnan(v) else v,
                1e-12,
            )
        add(case, "score", tok(got["score"][0]), None if math.isnan(r.score) else r.score, 1e-12)
        cls = {"estavel": 0, "vigilancia": 1, "alerta": 2, "indisponivel": 3}[r.classification]
        addi(case, "class", int(got["class"][0]), cls)
        mask = sum(bit for text, bit in ALERT_BITS for a in r.alerts if a.startswith(text))
        addi(case, "alerts", int(got["alerts"][0]), mask)


# ---------------------------------------------------------------- calib / atlas -----------------
def load_omni(files: List[Path]) -> pd.DataFrame:
    return pd.concat([_parse_omni2_text(f.read_text()) for f in files], ignore_index=True)


def calib(blocks: Dict[str, List[List[str]]]) -> None:
    for header, lines in blocks.items():
        if not header.startswith("calib "):
            continue
        files = [ROOT / p for p in header.split()[1:]]
        df = load_omni(files)
        dist = {d.variable: d for d in compute_empirical_distributions(df)}
        names = {
            "kp": "kp_index",
            "dst_abs": "dst_nt",
            "bz_south": "bz_gsm_nt",
            "pressure": "pressure_rho_v2",
            "kp_var": "kp_variability_12h",
        }
        got = {(l[0], l[1]): l[2] for l in lines if len(l) >= 3}
        case = f"calib {files[0].name}"
        for k, v in names.items():
            d = dist[v]
            addi(case, f"count {k}", int(got[("count", k)]), d.count)
            if d.count == 0:
                continue
            add(case, f"mean {k}", tok(got[("mean", k)]), d.mean, 1e-9)
            for q, py in (("p50", d.p50), ("p90", d.p90), ("p95", d.p95), ("p99", d.p99)):
                add(case, f"{q} {k}", tok(got[(q, k)]), py, 1e-9)


def atlas(blocks: Dict[str, List[List[str]]]) -> None:
    for header, lines in blocks.items():
        if not header.startswith("atlas "):
            continue
        parts = header.split()
        res, files = parts[1], [ROOT / p for p in parts[2:]]
        df = load_omni(files)
        # o parser Python corrigido já devolve Kp na escala real
        r = build_geomagnetic_atlas(df, res)
        case = f"atlas {res} {files[0].name}"
        sig = {s.period_label: s for s in r.signatures}
        rows = [l for l in lines if l[0] == "period"]
        addi(case, "n_periods", len(rows), len(sig))
        worst = 0.0
        bad = 0
        for l in rows:
            s = sig.get(l[1])
            if s is None:
                bad += 1
                continue
            sx = [tok(x) for x in l[2:5]] + [tok(l[7]), tok(l[8])]
            px = [s.mean_kp, s.mean_dst, s.mean_bz, s.min_dst, s.bz_southward_fraction]
            px = [None if (isinstance(x, float) and math.isnan(x)) else x for x in px]
            for a, b in zip(sx, px):
                rr = rel(a, b)
                if rr > 1e-9 and not (a is not None and b is not None and abs(a - b) < 1e-12):
                    bad += 1
                worst = max(worst, rr if math.isfinite(rr) else 1.0)
            if int(l[5]) != s.storm_hours or int(l[6]) != s.valid_hours:
                bad += 1
        ROWS.append(
            (
                case,
                f"{len(rows)} períodos, 7 campos cada",
                "-",
                "-",
                f"{worst:.2e}",
                "ok" if bad == 0 else f"DIVERGE ({bad})",
            )
        )


# ---------------------------------------------------------------- meta ---------------------------
def meta(blocks: Dict[str, List[List[str]]]) -> None:
    for header, lines in blocks.items():
        if not header.startswith("meta "):
            continue
        path = ROOT / header.split()[1]
        studies = []
        for ln in path.read_text().splitlines():
            t = ln.split("#")[0].split()
            if t and t[0] == "STUDY":
                studies.append(StudyEffect(t[1], float(t[2]), float(t[3]), 0, ""))
        r = AletheiaValidator().meta_analyze(studies)
        got = {l[0]: l[1] for l in lines if len(l) >= 2}
        case = f"meta {path.name}"
        for key, py in (
            ("Q", r.q_statistic),
            ("tau2", r.tau_squared),
            ("I2", r.i_squared),
            ("pooled_re", r.pooled_effect),
            ("ci_lo", r.pooled_ci_lower),
            ("ci_hi", r.pooled_ci_upper),
            ("z", r.z_score),
        ):
            add(case, key, tok(got[key]), py, 1e-9)


# ---------------------------------------------------------------- passport -----------------------
def read_case_arrays(path: Path) -> Tuple[np.ndarray, np.ndarray, int]:
    arrs: Dict[str, List[float]] = {"X": [], "Y": []}
    cur = ""
    lag = 0
    for ln in path.read_text().splitlines():
        t = ln.split()
        if not t:
            continue
        if t[0] in ("X", "Y"):
            cur = t[0]
            arrs[cur] += [float(v) for v in t[1:]]
        elif t[0] == "+":
            arrs[cur] += [float(v) for v in t[1:]]
        elif t[0] == "LAGMAX":
            lag = int(t[1])
    return np.asarray(arrs["X"]), np.asarray(arrs["Y"]), lag


def passport(blocks: Dict[str, List[List[str]]]) -> None:
    for header, lines in blocks.items():
        if not header.startswith("passport "):
            continue
        path = ROOT / header.split()[1]
        x, y, lag = read_case_arrays(path)
        got = {l[0]: l[1] for l in lines if len(l) == 2}
        # Python: scipy pearsonr por lag; `_cross_correlate_at_lags` devolve (melhor_lag, r)
        best_lag, r = _cross_correlate_at_lags(x, y, lag)
        case = f"passport {path.name}"
        add(case, "T_obs = |r(lag*)|", tok(got["T_obs"]), abs(r), 1e-9)
        addi(case, "lag_obs", int(got["lag_obs"]), best_lag)


def main() -> int:
    out = ROOT / "build" / "gate" / "twin_main.out"
    if not out.exists():
        print("rode `make sio-twin` antes (falta build/gate/twin_main.out)")
        return 0
    blocks = read_blocks(out)
    for fn in (helio, calib, atlas, meta, passport):
        try:
            fn(blocks)
        except Exception as e:  # noqa: BLE001  corroboração nunca derruba nada
            ROWS.append((fn.__name__, "(erro do runner Python)", "-", "-", "-", f"ERRO: {e}"))
    div = [r for r in ROWS if r[5] != "ok"]
    lines = [
        "# Corroboração Python × núcleo Sounio",
        "",
        "Python é `external_corroboration_only` (ADR-008/009): esta tabela REPORTA, nunca decide.",
        f"{len(ROWS)} comparações, {len(div)} divergências.",
        "",
        "| caso | grandeza | Sounio | Python | rel | status |",
        "|---|---|---|---|---|---|",
    ]
    lines += [
        f"| {c} | {q} | {s} | {p} | {r} | {st} |"
        for c, q, s, p, r, st in (div if div else ROWS[:0])
    ]
    if not div:
        lines.append("| (todas) | — | — | — | — | ok |")
    lines += [
        "",
        "<details><summary>Todas as comparações</summary>",
        "",
        "| caso | grandeza | Sounio | Python | rel | status |",
        "|---|---|---|---|---|---|",
    ]
    lines += [f"| {c} | {q} | {s} | {p} | {r} | {st} |" for c, q, s, p, r, st in ROWS]
    lines += ["", "</details>"]
    dest = ROOT / "build" / "corroboration"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "report.md").write_text("\n".join(lines) + "\n")
    print(
        f"corroboração: {len(ROWS)} comparações, {len(div)} divergências -> build/corroboration/report.md"
    )
    for r in div[:40]:
        print("  DIVERGE:", " | ".join(r))
    return 0  # nunca é hard-fail


if __name__ == "__main__":
    sys.exit(main())
