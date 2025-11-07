"""Modelos de dados públicos para heliobiologia.

Estas estruturas trazem dados geomagnéticos e solares em formato explícito,
facilitando integrações com pipelines puramente computacionais baseados em
datasets públicos.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass(slots=True)
class SolarIndex:
    """Representa um índice geomagnético ou solar em determinado timestamp."""

    timestamp: datetime
    value: float
    label: str


@dataclass(slots=True)
class SolarWindSample:
    """Amostra de vento solar (dados NOAA ACE/SWEPAM)."""

    timestamp: datetime
    speed_kms: float
    density_pcm3: float
    temperature_k: float


@dataclass(slots=True)
class IMFVector:
    """Componentes do campo magnético interplanetário (GSM)."""

    timestamp: datetime
    bx_nt: float
    by_nt: float
    bz_nt: float
    bt_nt: float


@dataclass(slots=True)
class SolarObservation:
    """Fotografia agregada dos principais indicadores solares."""

    kp_series: List[SolarIndex]
    dst_series: List[SolarIndex]
    solar_wind: List[SolarWindSample]
    imf: List[IMFVector]
    metadata: Optional[dict] = None



