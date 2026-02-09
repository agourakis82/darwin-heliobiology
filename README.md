# DARWIN Heliobiology

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18558930.svg)](https://doi.org/10.5281/zenodo.18558930)

Computational platform for heliobiological studies applied to mental health — NOAA/NASA data ingestion, psychodynamic modeling, and Q1 scientific validation.

## Structure
- `src/darwin_heliobiology/` — phenomenological core (SolarAtlas, SolarPsychodynamics, Kairos/Aletheia services).
- `analysis/`, `dashboards/`, `clinical/`, `simulations/`, `manuscripts/` — sprint deliverables.
- `docs/` — roadmap, dataset catalog, data lake, ethics.

See full manifesto in `README.exocortex`.

## Development
```bash
poetry install
poetry run pytest
poetry run black src
poetry run ruff src tests
poetry run mypy src
```

## Roadmap
See `docs/ROADMAP.md` for sprints and deliverables.

## SOTA References

- Updated overview in `docs/SOTA_HELIOBIOLOGY.md` (recommended models, datasets, and experiments).

## Citation

To cite this software, use:

```bibtex
@software{agourakis2025darwin,
  title={DARWIN Heliobiology: v0.2.0 — Scientific Grounding},
  author={Agourakis, Demetrios Chiuratto},
  year={2025},
  doi={10.5281/zenodo.18558930},
  url={https://zenodo.org/record/18558930}
}
```

See `CITATION.cff` for alternative formats.

## License
MIT.

## HelioMind Index

- Run `poetry run python scripts/build_heliomind_index.py --dry-run` to visualize the metric.
- Use `--output data/processed/heliomind_index.parquet` or `.json/.csv` to persist to data lake.

## HRV + Mood Pipeline

- Run `scripts/ingest_wesad.py --skip-download --extract-to <dir> --output data/processed/hrv_mood_wesad.csv` to process local WESAD files.
- Adjust `--window-minutes` and `--min-samples` parameters as needed (default 5min / 30 samples).
- Detailed specifications in `docs/HRV_MOOD_SPEC.md`.

