# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Darwin Heliobiology is a computational platform for heliobiological studies applied to mental health. It integrates NOAA/NASA solar data with wearable health metrics (HRV, mood) to investigate Sun-mental health correlations using only public datasets. The guiding principle: "Map the gradient between Sun and synapse."

## Commands

```bash
# Install dependencies
poetry install --with dev

# Run all tests (stops at first failure)
poetry run pytest

# Run a single test file
poetry run pytest tests/test_phase_space.py

# Run a single test by name
poetry run pytest -k "test_entropy"

# Tests with coverage
poetry run pytest --cov=src --cov-report=xml

# Format code
poetry run black src

# Lint
poetry run ruff check src tests

# Type check (strict mode)
poetry run mypy src
```

CI runs all four checks: `black --check`, `ruff check`, `mypy src`, `pytest --cov`.

## Architecture

### Phase Space Model (Central Concept)

The core abstraction is a 7-dimensional phase space **Ψ**:

```
Ψ = (SolarState, AutonomicRhythm, PsychometricTrajectory, CircadianFlux, RiskManifold)
```

`SolarPsychodynamics` (in `phase_space.py`) couples geomagnetic state (Kp, Dst, Bz) with biomarkers (HRV, mood, suicidality, circadian shift) and computes entropy/curvature over this space.

### Data Flow

```
NOAA/NASA APIs → SolarAtlas (core/solar_atlas.py)
                      ↓
              HelioMind Index (metrics/helio_index.py)
                      ↓
                      +
Public wearables (WESAD etc.) → HRV extraction (features/hrv.py)
                                      ↓
                              Mood normalization (preprocessing/mood.py)
                                      ↓
                              HRV+Mood pipeline (pipelines/hrv_mood.py)
                                      ↓
                      SolarPsychodynamics (phase_space.py)
                              ↓                    ↓
               KairosForecaster          AletheiaValidator
              (services/)                (services/)
```

### Source Layout (`src/darwin_heliobiology/`)

- **`phase_space.py`** — `SolarPsychodynamics`: the central 7D phase space model
- **`core/solar_atlas.py`** — `SolarAtlas`: NOAA/NASA public data ingestion (Kp, Dst, Bz, solar wind)
- **`core/psychophysiology.py`** — `AutonomicSnapshot`: RR intervals to HRV stats, geomagnetic sensitivity
- **`models/solar.py`** — Domain dataclasses: `SolarIndex`, `SolarWindSample`, `IMFVector`, `OMNIHourlyRecord`
- **`features/hrv.py`** — HRV metric extraction (RMSSD, SDNN, pNN50, sample entropy)
- **`preprocessing/mood.py`** — Likert scale normalization to [0,1], mood labeling (estavel/vigilancia/alerta)
- **`metrics/helio_index.py`** — `HelioMindIndexResult`: composite solar activity score [0..1]
- **`core/geomagnetic_atlas.py`** — Temporal geomagnetic signature atlas (daily/monthly/quarterly profiles)
- **`pipelines/`** — `hrv_mood.py` (HRV+mood records), `heliomind_builder.py` (solar index pipeline), `neural_forecast.py` (TFT/PatchTST), `calibration.py` (empirical calibration against OMNI2)
- **`services/kairos_forecaster.py`** — Hybrid forecaster (exponential smoothing + Bayesian regression)
- **`services/aletheia_validator.py`** — Validates correlations + DerSimonian-Laird random-effects meta-analysis
- **`services/causal_discovery.py`** — PCMCI+ causal discovery with heliobiological priors via tigramite
- **`services/passport.py`** — Psycho-geomagnetic passport: individual sensitivity calibration via cross-correlation
- **`datasets/`** — Public dataset catalog, WESAD ingestion, NOAA raw cache, OMNI2 hourly, WHO mortality

### Key Domain Entities (from ONTOLOGY.md)

- **SolarState**: vector {Kp, Dst, Bz, solar_flux, CME_probability}
- **AutonomicRhythm**: HRV metrics, actigraphy, salivary cortisol
- **PsychometricTrajectory**: time series of PHQ-9, MADRS, PANSS, suicidality scales
- **RiskManifold**: generative embedding for decompensation probability (0..1)
- Singularities = extreme events (Kp >= 7, Dst <= -100) — suicidality threshold removed (no empirical basis)

### Scientific Grounding

All constants and thresholds are graded A–D per `docs/SCIENTIFIC_FOUNDATIONS.md`:
- **A (Strong)**: Cardiovascular RR 1.1–1.5 during geomag storms; Kp/Dst/Bz NOAA scales
- **B (Moderate)**: HRV–geomag (Ong et al. 2022, n=809, RMSSD -14.7ms per Kp IQR)
- **C (Weak)**: Mental health/suicide correlations (ecological, confounded by seasonality)
- **D (Exploratory)**: HelioMind weights, wind pressure normalization, sensitivity formula

Ethics and data governance: `docs/ETHICS_COMPLIANCE.md`.

## Code Style & Conventions

- **Python 3.11**, managed with **Poetry**
- **Black** formatter, line-length 100, target py311
- **Ruff** for linting
- **MyPy strict mode** — all code must pass strict type checking
- Dataclasses with `__slots__` for memory-efficient immutable structures
- Pydantic for validation at boundaries
- Test coverage target: >= 85%
- All data sources must be public and reproducible — no proprietary datasets
- Documentation language is Portuguese; code (identifiers, docstrings) mixes Portuguese labels with English API names

### Patterns

- **Script/module separation**: business logic in `src/darwin_heliobiology/` (datasets, pipelines), thin CLI wrappers in `scripts/` using argparse + `main()`. Scripts delegate to modules, never contain domain logic.
- **Persistence**: DataFrames are persisted using suffix dispatch on output `Path` (`.parquet`/`.csv`/`.json`). `mkdir(parents=True, exist_ok=True)` before writing.
- **Testing**: no real HTTP calls. Mock `SolarAtlas._get_json` via `monkeypatch.setattr` for NOAA tests. Use `tmp_path` fixture for file I/O. For ZIP downloads, use in-memory `BytesIO` + `ZipFile` fakes.

## CLI Scripts

```bash
# Build HelioMind Index from live NOAA data
poetry run python scripts/build_heliomind_index.py --hours 24 --output data/processed/heliomind_index.parquet

# Ingest WESAD dataset and extract HRV+mood features
poetry run python scripts/ingest_wesad.py --zip-path data/raw/hrv_mood/wesad/WESAD.zip --extract-to data/raw/hrv_mood/wesad/extracted --output data/processed/hrv_mood_wesad.csv --window-minutes 5

# Fetch and cache raw NOAA SWPC indices (Kp, Dst, solar wind, IMF)
poetry run python scripts/fetch_noaa.py --hours 24 --output-dir data/raw/noaa --format parquet

# Download OMNI2 hourly data from NASA OMNIWeb
poetry run python scripts/fetch_omni.py --years 2024 2025 --output-dir data/raw/nasa_omni

# Download WHO mortality CSVs
poetry run python scripts/fetch_who.py --output-dir data/raw/who

# Generic HRV+mood pipeline from any CSV with timestamp + rr_ms columns
poetry run python scripts/build_hrv_mood_pipeline.py --input data/raw/rr_data.csv --output data/processed/hrv_mood_features.parquet --window-minutes 5

# Build geomagnetic atlas from OMNI2 data
poetry run python scripts/build_geomagnetic_atlas.py --input data/raw/nasa_omni/omni2_hourly.parquet --resolution monthly --output data/processed/geomagnetic_atlas.parquet

# Run TFT/PatchTST neural forecast
poetry run python scripts/run_neural_forecast.py --solar-input data/processed/heliomind_index.parquet --model tft --horizon 24 --output data/processed/neural_forecast.parquet

# Run PCMCI+ causal discovery
poetry run python scripts/run_causal_discovery.py --solar-input data/raw/nasa_omni/omni2_hourly.parquet --hrv-input data/processed/hrv_mood_wesad.csv --tau-max 48 --use-priors --output data/processed/causal_links.parquet

# Build psycho-geomagnetic passport for a subject
poetry run python scripts/build_passport.py --hrv-input data/processed/hrv_mood_wesad.csv --solar-input data/raw/nasa_omni/omni2_hourly.parquet --subject-id S2 --output data/processed/passport/S2_passport.parquet

# Calibrate HelioMind Index against OMNI2 data (empirical p99 normalization)
poetry run python scripts/calibrate_heliomind.py --omni-input data/raw/nasa_omni/omni2_hourly.parquet --output data/processed/calibration_report.parquet --apply

# Validate PCMCI+ pipeline on solar-only variables (no HRV)
poetry run python scripts/validate_solar_pcmci.py --omni-input data/raw/nasa_omni/omni2_hourly.parquet --tau-max 24 --alpha 0.05 --output data/processed/causal_solar_validation.parquet
```

## Agent Autonomy

Per project guidelines (docs/agents/AGENT_AUTONOMY.md): execute scripts, run analyses, and automate repetitive tasks freely. Register key discoveries. Prefer declarative pipelines and reproducible dashboards.
