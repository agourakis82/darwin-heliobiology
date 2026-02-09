"""Cálculo do HelioMind Index.

Mostra a acoplagem Sol ↔ neurofisiologia em uma janela curta usando apenas dados públicos.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np
from numpy.typing import NDArray

from darwin_heliobiology.models.solar import IMFVector, SolarObservation, SolarWindSample

FloatArray = NDArray[np.float64]


@dataclass(slots=True)
class HelioMindComponents:
    """Componentes normalizados do HelioMind Index (0.0 – 1.0)."""

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


def compute_helio_mind_index(snapshot: SolarObservation) -> HelioMindIndexResult:
    """Calcula o HelioMind Index a partir de um ``SolarObservation``.

    Parameters
    ----------
    snapshot:
        Observação consolidada retornada por :class:`~darwin_heliobiology.core.solar_atlas.SolarAtlas`.

    Returns
    -------
    HelioMindIndexResult
        Estrutura com score composto, componentes normalizados e alertas interpretáveis.
    """

    kp_values = _extract_index_values([idx.value for idx in snapshot.kp_series])
    dst_values = _extract_index_values([idx.value for idx in snapshot.dst_series])
    bz_values = _extract_imf_component(snapshot.imf)
    wind_speed = _extract_wind_component(snapshot.solar_wind, attr="speed_kms")
    wind_density = _extract_wind_component(snapshot.solar_wind, attr="density_pcm3")

    components = HelioMindComponents(
        kp_activity=_normalize_kp(kp_values),
        dst_storm_intensity=_normalize_dst(dst_values),
        bz_reconnection=_normalize_bz(bz_values),
        solar_wind_pressure=_normalize_wind_pressure(wind_speed, wind_density),
        variability=_normalize_variability(kp_values),
    )

    # Pesos EXPLORATÓRIOS (grau D) — a ordenação relativa (Kp > Dst > Bz) reflete
    # a frequência de uso na literatura epidemiológica, mas os valores numéricos
    # não derivam de estudo empírico.  Calibrar via regressão sobre desfechos
    # clínicos antes de publicar.  Ver docs/SCIENTIFIC_FOUNDATIONS.md §5.1.
    score = float(
        np.clip(
            0.35 * components.kp_activity
            + 0.25 * components.dst_storm_intensity
            + 0.20 * components.bz_reconnection
            + 0.15 * components.solar_wind_pressure
            + 0.05 * components.variability,
            0.0,
            1.0,
        )
    )
    classification = _classify(score)
    alerts = _build_alerts(components)

    timestamp = _latest_timestamp(
        snapshot,
        default=datetime.now(tz=timezone.utc),
    )

    metadata = dict(snapshot.metadata or {})
    metadata.setdefault("window_hours", metadata.get("window_hours", 24))

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


def _extract_index_values(values: List[float]) -> FloatArray:
    if not values:
        return np.zeros(0, dtype=np.float64)
    return np.asarray(values, dtype=np.float64)


def _extract_imf_component(vectors: List[IMFVector]) -> FloatArray:
    if not vectors:
        return np.zeros(0, dtype=np.float64)
    return np.asarray([vec.bz_nt for vec in vectors], dtype=np.float64)


def _extract_wind_component(samples: List[SolarWindSample], attr: str) -> FloatArray:
    if not samples:
        return np.zeros(0, dtype=np.float64)
    return np.asarray([getattr(sample, attr) for sample in samples], dtype=np.float64)


def _normalize_kp(kp_values: FloatArray) -> float:
    """Escala Kp oficial NOAA: 0–9 (grau A)."""
    if kp_values.size == 0:
        return 0.0
    window = kp_values[-min(12, kp_values.size) :]
    return float(np.clip(np.mean(window) / 9.0, 0.0, 1.0))


def _normalize_dst(dst_values: FloatArray) -> float:
    """Dst extremo histórico ≈ -300 nT (Bastille Day 2000: -301 nT). Grau A."""
    if dst_values.size == 0:
        return 0.0
    min_dst = float(np.min(dst_values))
    storm = abs(min(min_dst, 0.0))
    return float(np.clip(storm / 300.0, 0.0, 1.0))


def _normalize_bz(bz_values: FloatArray) -> float:
    """Bz extremo em tempestades G4/G5 ≈ -15 a -25 nT; 20 nT como cap razoável. Grau A."""
    if bz_values.size == 0:
        return 0.0
    southward = np.clip(-bz_values, 0, None)
    return float(np.clip(np.mean(southward) / 20.0, 0.0, 1.0))


def _normalize_wind_pressure(speed: FloatArray, density: FloatArray) -> float:
    """Pressão dinâmica ρv²; divisor 300k é EXPLORATÓRIO (grau D)."""
    if speed.size == 0 or density.size == 0:
        return 0.0
    pressure = density * np.square(speed)
    return float(np.clip(np.mean(pressure) / 300_000.0, 0.0, 1.0))


def _normalize_variability(kp_values: FloatArray) -> float:
    """std(Kp) / 2.5 — divisor EXPLORATÓRIO (grau D), sem referência empírica."""
    if kp_values.size < 2:
        return 0.0
    window = kp_values[-min(12, kp_values.size) :]
    return float(np.clip(np.std(window, dtype=np.float64) / 2.5, 0.0, 1.0))


def _classify(score: float) -> str:
    if score < 0.33:
        return "estavel"
    if score < 0.66:
        return "vigilancia"
    return "alerta"


def _build_alerts(components: HelioMindComponents) -> List[str]:
    # Limiares baseados em escalas NOAA G1–G5 (Kp, Dst, Bz) — grau A.
    # Pressão e variabilidade são EXPLORATÓRIOS (grau D).
    # "risco neuropsicofisiologico" — evidência cardiovascular (grau A),
    # evidência psiquiátrica (grau C). Ver docs/SCIENTIFIC_FOUNDATIONS.md §5.3.
    alerts: List[str] = []
    if components.kp_activity >= 0.7:  # ~Kp 6.3 ≈ G3 (NOAA)
        alerts.append("Kp elevado — tempestade geomagnetica em curso")
    if components.dst_storm_intensity >= 0.6:  # ~Dst -180 nT — tempestade severa
        alerts.append("Dst muito negativo — risco cardiovascular elevado (RR ~1.1–1.5)")
    if components.bz_reconnection >= 0.5:  # ~Bz -10 nT — reconexão significativa
        alerts.append("Bz sul intenso — reconexao magnética acentuada")
    if components.solar_wind_pressure >= 0.5:  # EXPLORATÓRIO
        alerts.append("Pressao de vento solar acima da média")
    if components.variability >= 0.6:  # EXPLORATÓRIO
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
