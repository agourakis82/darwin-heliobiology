"""Cálculo do HelioMind Index.

Mostra a acoplagem Sol ↔ neurofisiologia em uma janela curta usando apenas dados públicos.

Constantes de normalização calibradas contra OMNI2 2020-2025 (52 608 registros horários).
Divisores = percentil 99 empírico de cada variável transformada.
Ver docs/SCIENTIFIC_FOUNDATIONS.md §5.2 e data/processed/calibration_constants.json.
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
class NormalizationConstants:
    """Constantes de normalização para o HelioMind Index.

    Valores default calibrados contra OMNI2 2020-2025 (p99 empírico).
    Kp usa a escala oficial NOAA 0-9 (grau A).
    """

    kp_divisor: float = 9.0  # Escala NOAA oficial 0-9 (grau A)
    dst_divisor: float = 78.0  # p99 de abs(min(Dst,0)), OMNI2 2020-2025 (grau B)
    bz_divisor: float = 8.7  # p99 de max(-Bz,0), OMNI2 2020-2025 (grau B)
    pressure_divisor: float = 4_364_643.0  # p99 de ρv², OMNI2 2020-2025 (grau B)
    variability_divisor: float = 1.57  # p99 de std(Kp,12h), OMNI2 2020-2025 (grau B)


#: Constantes default, calibradas empiricamente.
DEFAULT_CONSTANTS = NormalizationConstants()


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


def compute_helio_mind_index(
    snapshot: SolarObservation,
    constants: Optional[NormalizationConstants] = None,
) -> HelioMindIndexResult:
    """Calcula o HelioMind Index a partir de um ``SolarObservation``.

    Parameters
    ----------
    snapshot:
        Observação consolidada retornada por :class:`~darwin_heliobiology.core.solar_atlas.SolarAtlas`.
    constants:
        Constantes de normalização. Default: calibradas contra OMNI2 2020-2025.

    Returns
    -------
    HelioMindIndexResult
        Estrutura com score composto, componentes normalizados e alertas interpretáveis.
    """
    c = constants or DEFAULT_CONSTANTS

    kp_values = _extract_index_values([idx.value for idx in snapshot.kp_series])
    dst_values = _extract_index_values([idx.value for idx in snapshot.dst_series])
    bz_values = _extract_imf_component(snapshot.imf)
    wind_speed = _extract_wind_component(snapshot.solar_wind, attr="speed_kms")
    wind_density = _extract_wind_component(snapshot.solar_wind, attr="density_pcm3")

    components = HelioMindComponents(
        kp_activity=_normalize_kp(kp_values, divisor=c.kp_divisor),
        dst_storm_intensity=_normalize_dst(dst_values, divisor=c.dst_divisor),
        bz_reconnection=_normalize_bz(bz_values, divisor=c.bz_divisor),
        solar_wind_pressure=_normalize_wind_pressure(
            wind_speed, wind_density, divisor=c.pressure_divisor
        ),
        variability=_normalize_variability(kp_values, divisor=c.variability_divisor),
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


def _normalize_kp(kp_values: FloatArray, *, divisor: float = 9.0) -> float:
    """Escala Kp oficial NOAA: 0–9 (grau A). Divisor fixo = 9.0."""
    if kp_values.size == 0:
        return 0.0
    window = kp_values[-min(12, kp_values.size) :]
    return float(np.clip(np.mean(window) / divisor, 0.0, 1.0))


def _normalize_dst(dst_values: FloatArray, *, divisor: float = 78.0) -> float:
    """abs(min(Dst,0)) / divisor. Calibrado: p99 = 78 nT (OMNI2 2020-2025, grau B)."""
    if dst_values.size == 0:
        return 0.0
    min_dst = float(np.min(dst_values))
    storm = abs(min(min_dst, 0.0))
    return float(np.clip(storm / divisor, 0.0, 1.0))


def _normalize_bz(bz_values: FloatArray, *, divisor: float = 8.7) -> float:
    """max(-Bz,0) / divisor. Calibrado: p99 = 8.7 nT (OMNI2 2020-2025, grau B)."""
    if bz_values.size == 0:
        return 0.0
    southward = np.clip(-bz_values, 0, None)
    return float(np.clip(np.mean(southward) / divisor, 0.0, 1.0))


def _normalize_wind_pressure(
    speed: FloatArray, density: FloatArray, *, divisor: float = 4_364_643.0
) -> float:
    """ρv² / divisor. Calibrado: p99 = 4.36M (OMNI2 2020-2025, grau B)."""
    if speed.size == 0 or density.size == 0:
        return 0.0
    pressure = density * np.square(speed)
    return float(np.clip(np.mean(pressure) / divisor, 0.0, 1.0))


def _normalize_variability(kp_values: FloatArray, *, divisor: float = 1.57) -> float:
    """std(Kp,12h) / divisor. Calibrado: p99 = 1.57 (OMNI2 2020-2025, grau B)."""
    if kp_values.size < 2:
        return 0.0
    window = kp_values[-min(12, kp_values.size) :]
    return float(np.clip(np.std(window, dtype=np.float64) / divisor, 0.0, 1.0))


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
    # Ver docs/SCIENTIFIC_FOUNDATIONS.md §5.3.
    alerts: List[str] = []
    if components.kp_activity >= 0.7:  # Kp ≥ 6.3 ≈ G3 (NOAA)
        alerts.append("Kp elevado — tempestade geomagnetica em curso")
    if components.dst_storm_intensity >= 0.6:  # |Dst| ≥ 47 nT (≈ top 5% das horas)
        alerts.append("Dst muito negativo — risco cardiovascular elevado (RR ~1.1–1.5)")
    if components.bz_reconnection >= 0.5:  # Bz sul ≥ 4.4 nT (≈ top 8% das horas)
        alerts.append("Bz sul intenso — reconexao magnética acentuada")
    if components.solar_wind_pressure >= 0.5:  # ρv² ≥ 2.2M (EXPLORATÓRIO)
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
