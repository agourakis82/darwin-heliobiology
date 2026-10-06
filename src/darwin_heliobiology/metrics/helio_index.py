"""Cálculo do HelioMind Index.

Mostra a acoplagem Sol ↔ neurofisiologia em uma janela curta usando apenas dados públicos.

Constantes de normalização calibradas contra OMNI2 2020-2025 (52 608 registros horários).
Divisores = percentil 99 empírico de cada variável transformada.
Ver docs/SCIENTIFIC_FOUNDATIONS.md §5.2 e data/processed/calibration_constants.json.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional, Sequence

import numpy as np
from numpy.typing import NDArray

from darwin_heliobiology.models.solar import SolarObservation

FloatArray = NDArray[np.float64]


#: Largura da janela de agregação (por TEMPO, não por número de amostras).
WINDOW_HOURS = 12

#: Constante de pressão dinâmica: P[nPa] = 1.6726e-6 · n[cm⁻³] · v²[km/s]².
PRESSURE_COEFF_NPA = 1.6726e-6


@dataclass(slots=True)
class NormalizationConstants:
    """Constantes de normalização para o HelioMind Index.

    Valores default calibrados contra OMNI2 2020-2025 (p99 empírico).
    Kp usa a escala oficial NOAA 0-9 (grau A).
    """

    kp_divisor: float = 9.0  # Escala NOAA oficial 0-9 (grau A)
    dst_divisor: float = 78.0  # p99 de abs(min(Dst,0)), OMNI2 2020-2025 (grau B)
    bz_divisor: float = 8.7  # p99 de max(-Bz,0), OMNI2 2020-2025 (grau B)
    pressure_divisor: float = 7.30  # p99 de 1.6726e-6·n·v² [nPa], OMNI2 2020-2025 (grau B)
    variability_divisor: float = 1.57  # p99 de std(Kp,12h), ddof=1 (grau B)


#: Constantes default, calibradas empiricamente.
DEFAULT_CONSTANTS = NormalizationConstants()

#: Pesos default (kp, dst, bz, pressão, variabilidade). Somam 1.0.
WEIGHTS = (0.35, 0.25, 0.20, 0.15, 0.05)

#: Rótulo de classificação quando o score não pode ser calculado.
UNAVAILABLE = "indisponivel"


@dataclass(slots=True)
class HelioMindComponents:
    """Componentes normalizados do HelioMind Index (0.0 – 1.0).

    ``NaN`` significa AUSENTE (nenhuma amostra válida na janela). Ausente nunca
    é convertido em 0.0: um componente zerado diria "calmo" onde não há dado.
    """

    kp_activity: float
    dst_storm_intensity: float
    bz_reconnection: float
    solar_wind_pressure: float
    variability: float


@dataclass(slots=True)
class HelioMindIndexResult:
    """Resultado final do HelioMind Index para uma janela temporal."""

    timestamp: datetime
    score: float
    classification: str
    components: HelioMindComponents
    alerts: List[str]
    metadata: Dict[str, Any]


def compute_helio_mind_index(
    snapshot: SolarObservation,
    constants: Optional[NormalizationConstants] = None,
) -> HelioMindIndexResult:
    """Calcula o HelioMind Index a partir de um ``SolarObservation``.

    A janela é de ``WINDOW_HOURS`` horas contadas a partir da amostra mais recente
    de qualquer série (por tempo). Amostras NaN são descartadas. Se algum
    componente não tem nenhuma amostra válida, o score é ``NaN`` e a classe é
    ``"indisponivel"`` — nunca um valor fabricado.
    """
    c = constants or DEFAULT_CONSTANTS

    timestamp = _latest_timestamp(snapshot, default=datetime.now(tz=timezone.utc))
    cutoff = timestamp - timedelta(hours=WINDOW_HOURS)

    kp_values = _window_values(snapshot.kp_series, cutoff, lambda i: i.value)
    dst_values = _window_values(snapshot.dst_series, cutoff, lambda i: i.value)
    bz_values = _window_values(snapshot.imf, cutoff, lambda v: v.bz_nt)
    pressure_values = _window_values(
        snapshot.solar_wind,
        cutoff,
        lambda w: PRESSURE_COEFF_NPA * w.density_pcm3 * w.speed_kms**2,
    )

    components = HelioMindComponents(
        kp_activity=_normalize_kp(kp_values, divisor=c.kp_divisor),
        dst_storm_intensity=_normalize_dst(dst_values, divisor=c.dst_divisor),
        bz_reconnection=_normalize_bz(bz_values, divisor=c.bz_divisor),
        solar_wind_pressure=_normalize_wind_pressure(pressure_values, divisor=c.pressure_divisor),
        variability=_normalize_variability(kp_values, divisor=c.variability_divisor),
    )

    # Pesos default (grau C quando calibrados via WHO, grau D quando arbitrários).
    # Ver docs/SCIENTIFIC_FOUNDATIONS.md §5.1.
    parts = (
        components.kp_activity,
        components.dst_storm_intensity,
        components.bz_reconnection,
        components.solar_wind_pressure,
        components.variability,
    )
    if any(math.isnan(p) for p in parts):
        score = float("nan")
        classification = UNAVAILABLE
    else:
        score = float(np.clip(sum(w * p for w, p in zip(WEIGHTS, parts, strict=True)), 0.0, 1.0))
        classification = _classify(score)
    alerts = _build_alerts(components)

    metadata = dict(snapshot.metadata or {})
    metadata["window_hours"] = WINDOW_HOURS

    return HelioMindIndexResult(
        timestamp=timestamp,
        score=score,
        classification=classification,
        components=components,
        alerts=alerts,
        metadata=metadata,
    )


# ---------------------------------------------------------------------------
# Helpers de normalização
# ---------------------------------------------------------------------------


def _window_values(
    items: Sequence[Any], cutoff: datetime, getter: Callable[[Any], float]
) -> FloatArray:
    """Valores finitos das amostras com ``timestamp > cutoff`` (janela por tempo)."""
    out: List[float] = []
    for item in items:
        if item.timestamp <= cutoff:
            continue
        v = getter(item)
        if v is None or not math.isfinite(v):
            continue
        out.append(float(v))
    return np.asarray(out, dtype=np.float64)


_ABSENT = float("nan")


def _normalize_kp(kp_values: FloatArray, *, divisor: float = 9.0) -> float:
    """Kp oficial NOAA 0–9 (grau A): média da janela / 9."""
    if kp_values.size == 0:
        return _ABSENT
    return float(np.clip(np.mean(kp_values) / divisor, 0.0, 1.0))


def _normalize_dst(dst_values: FloatArray, *, divisor: float = 78.0) -> float:
    """abs(min(Dst,0)) / divisor. Calibrado: p99 = 78 nT (OMNI2 2020-2025, grau B)."""
    if dst_values.size == 0:
        return _ABSENT
    storm = abs(min(float(np.min(dst_values)), 0.0))
    return float(np.clip(storm / divisor, 0.0, 1.0))


def _normalize_bz(bz_values: FloatArray, *, divisor: float = 8.7) -> float:
    """mean(max(-Bz,0)) / divisor. Calibrado: p99 = 8.7 nT (OMNI2 2020-2025, grau B)."""
    if bz_values.size == 0:
        return _ABSENT
    southward = np.clip(-bz_values, 0, None)
    return float(np.clip(np.mean(southward) / divisor, 0.0, 1.0))


def _normalize_wind_pressure(pressure_npa: FloatArray, *, divisor: float = 7.30) -> float:
    """mean(1.6726e-6·n·v²) [nPa] / divisor. Calibrado: p99 = 7.30 nPa (grau B)."""
    if pressure_npa.size == 0:
        return _ABSENT
    return float(np.clip(np.mean(pressure_npa) / divisor, 0.0, 1.0))


def _normalize_variability(kp_values: FloatArray, *, divisor: float = 1.57) -> float:
    """std(Kp, janela de 12 h, ddof=1) / divisor. Precisa de ≥ 2 amostras."""
    if kp_values.size < 2:
        return _ABSENT
    return float(np.clip(np.std(kp_values, ddof=1, dtype=np.float64) / divisor, 0.0, 1.0))


def _classify(score: float) -> str:
    if score < 0.33:
        return "estavel"
    if score < 0.66:
        return "vigilancia"
    return "alerta"


def _build_alerts(components: HelioMindComponents) -> List[str]:
    # Limiares em fração do p99 calibrado (OMNI2 2020-2025).
    # 0.6 ≈ top 5-10% das horas; 0.7 ≈ top 2-3%.
    # Evidência cardiovascular (grau A), psiquiátrica (grau C).
    # Ver docs/SCIENTIFIC_FOUNDATIONS.md §5.3. Componente ausente (NaN) não alerta.
    alerts: List[str] = []
    if components.kp_activity >= 0.7:  # Kp ≥ 6.3 ≈ G3 (NOAA)
        alerts.append("Kp elevado — tempestade geomagnetica em curso")
    if components.dst_storm_intensity >= 0.6:  # |Dst| ≥ 47 nT (≈ top 5% das horas)
        alerts.append("Dst muito negativo — risco cardiovascular elevado (RR ~1.1–1.5)")
    if components.bz_reconnection >= 0.5:  # Bz sul ≥ 4.4 nT (≈ top 8% das horas)
        alerts.append("Bz sul intenso — reconexao magnética acentuada")
    if components.solar_wind_pressure >= 0.5:  # P ≥ 3.65 nPa (EXPLORATÓRIO)
        alerts.append("Pressao de vento solar acima da média")
    if components.variability >= 0.6:  # std(Kp) ≥ 0.94 (EXPLORATÓRIO)
        alerts.append("Variabilidade geomagnetica alta — flutuações rápidas")
    return alerts


def _latest_timestamp(snapshot: SolarObservation, default: Optional[datetime] = None) -> datetime:
    candidates: List[datetime] = []
    if snapshot.kp_series:
        candidates.append(snapshot.kp_series[-1].timestamp)
    if snapshot.dst_series:
        candidates.append(snapshot.dst_series[-1].timestamp)
    if snapshot.imf:
        candidates.append(snapshot.imf[-1].timestamp)
    if snapshot.solar_wind:
        candidates.append(snapshot.solar_wind[-1].timestamp)
    if not candidates:
        return default if default is not None else datetime.now(tz=timezone.utc)
    return max(candidates)
