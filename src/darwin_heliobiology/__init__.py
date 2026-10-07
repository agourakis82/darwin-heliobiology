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
from .datasets.public_sources import PUBLIC_DATASETS, DatasetReference
from .metrics.helio_index import (
    HelioMindComponents,
    HelioMindIndexResult,
    compute_helio_mind_index,
)
from .phase_space import SolarPsychodynamics
from .services import (
    AletheiaValidator,
    ForecastResult,
    KairosForecaster,
    ScientificExpectation,
)

__all__ = [
    "PUBLIC_DATASETS",
    "AletheiaValidator",
    "AutonomicSnapshot",
    "DatasetReference",
    "ForecastResult",
    "HelioMindComponents",
    "HelioMindIndexResult",
    "KairosForecaster",
    "ScientificExpectation",
    "SolarAtlas",
    "SolarPsychodynamics",
    "aggregate_hrv_series",
    "compute_helio_mind_index",
    "merge_multimodal",
    "mood_normalization",
]
