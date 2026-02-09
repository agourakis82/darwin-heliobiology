# Changelog

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
