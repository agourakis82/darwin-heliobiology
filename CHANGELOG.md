# Changelog

## [Unreleased] - fix/data-integrity

Integridade de dados (ausente nunca vira 0; escalas e janelas explícitas):

- OMNI2: Kp é dividido por 10 NA LEITURA (`_parse_omni2_text`); `ensure_kp_scale` (série inteira, idempotente) substitui as heurísticas `max > 9.5` espalhadas. Parquet legado migrado por `scripts/migrate_omni_kp_scale.py`.
- HelioMind Index: janela de 12 h por TEMPO (antes: últimas 12 amostras, de uma série de 1 min); `std` com ddof=1 (igual à calibração); componente sem amostra válida é `NaN` e o score vira `NaN`/`indisponivel` (antes: 0.0 / "estavel"); pressão dinâmica em nPa (1.6726e-6·n·v² / 7.30).
- Atlas geomagnético: `storm_count` → `storm_hours` (+ `valid_hours`); contagem com Kp na escala real (antes `Kp>=5` sobre ×10 contava quase toda hora); médias/mínimos sem dado são `NaN`, não 0.0.
- SolarAtlas (NOAA): campo ausente descarta a amostra / vira `NaN` (antes: `0.0` default para Kp, velocidade, densidade, Bz).
- Calibração/WHO: variabilidade std(Kp,12 h) por tempo com ddof=1; o placeholder `variability = 0.0` e `Bz = 0.0` ausentes viraram `NaN`.
- Fisher-z recusa |r| = 1.
- HelioMind: `_latest_timestamp` toma o MAIOR timestamp de todas as séries (antes o último elemento de cada lista, que no feed RTSW decrescente é a amostra mais antiga; issue #3).

## [0.2.0] - 2025-02-09

- **DOI Published**: [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18558930.svg)](https://doi.org/10.5281/zenodo.18558930)
- Added scientific evidence grading system (A–D) in `docs/SCIENTIFIC_FOUNDATIONS.md`
- Added ethics compliance and governance guide in `docs/ETHICS_COMPLIANCE.md`
- Reclassified exploratory model weights as "grade D"
- Removed unsupported mental health thresholds
- Adjusted correlation expectations to r=(0.05, 0.25) based on actual effect sizes
- Scientific documentation with 12 DOI-verified references
- Strengthened evidence for cardiovascular impacts during geomagnetic storms (RR 1.1–1.5, n>500k)
- Moderate support for heart rate variability associations
- Clarification of methodological limitations for mental health correlations

## [0.1.0] - 2025-11-07

- Created `darwin-heliobiology` package with phenomenological phase space.
- Included manifesto (`README.exocortex`) and domain ontology.
- Initial tests to verify curvature/entropy calculations.
- Added HelioMind Index with normalized metrics and ingestion pipeline.
- CLI `scripts/build_heliomind_index.py` to export dataframe as JSON/CSV.
- HRV + mood pipeline with temporal resampling and multi-scale normalization.
- WESAD ingestion via `scripts/ingest_wesad.py` (download, extraction, and Parquet/CSV export).
- Heliobiology SOTA overview (docs/SOTA_HELIOBIOLOGY.md) with prioritized models and datasets.
