"""Catalogo de datasets públicos relevantes para heliobiologia."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(slots=True)
class DatasetReference:
    name: str
    description: str
    url: str
    license: str


PUBLIC_DATASETS: Dict[str, DatasetReference] = {
    "noaa_swpc": DatasetReference(
        name="NOAA Space Weather Prediction Center",
        description="Índices geomagnéticos e vento solar (Kp, Dst, ACE).",
        url="https://services.swpc.noaa.gov/",
        license="Public Domain (NOAA)"
    ),
    "nasa_omni": DatasetReference(
        name="NASA OMNIWeb",
        description="Séries históricas solares e geomagnéticas combinadas.",
        url="https://omniweb.gsfc.nasa.gov/",
        license="Public Domain (NASA)"
    ),
    "who_mortality": DatasetReference(
        name="WHO Mortality Database",
        description="Taxas de mortalidade, incluindo suicídio, por país/ano.",
        url="https://www.who.int/data/data-collection-tools/who-mortality-database",
        license="Open Access"
    ),
    "ghe_fatal": DatasetReference(
        name="Global Health Estimates",
        description="Estimativas globais de doença mental e suicídio.",
        url="https://www.who.int/data/gho/data/themes/mortality-and-global-health-estimates",
        license="Open Access"
    ),
    "uk_biobank": DatasetReference(
        name="UK Biobank",
        description="Dados clínicos e ambientais (acesso mediante aprovação).",
        url="https://www.ukbiobank.ac.uk/",
        license="Application Required"
    )
}



