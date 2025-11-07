"""darwin-heliobiology core package.

Institucionaliza o espaço de fase heliobiológico com pipelines puramente
computacionais e datasets públicos.
"""

from .core.psychophysiology import (
    AutonomicSnapshot,
    aggregate_hrv_series,
    merge_multimodal,
    mood_normalization,
)
from .core.solar_atlas import SolarAtlas
from .datasets.public_sources import DatasetReference, PUBLIC_DATASETS
from .phase_space import SolarPsychodynamics
from .services import AletheiaValidator, ForecastResult, KairosForecaster, ScientificExpectation
from .metrics.helio_index import HelioMindIndexResult, HelioMindComponents, compute_helio_mind_index

__all__ = [
    "SolarAtlas",
    "SolarPsychodynamics",
    "AutonomicSnapshot",
    "aggregate_hrv_series",
    "merge_multimodal",
    "mood_normalization",
    "PUBLIC_DATASETS",
    "DatasetReference",
    "KairosForecaster",
    "ForecastResult",
    "AletheiaValidator",
    "ScientificExpectation",
    "HelioMindIndexResult",
    "HelioMindComponents",
    "compute_helio_mind_index",
]
