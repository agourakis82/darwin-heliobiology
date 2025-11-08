# DARWIN Heliobiology

Plataforma computacional para estudos heliobiológicos aplicados à saúde mental — ingestão NOAA/NASA, modelagem psicodinâmica e validação científica nível Q1.

## Estrutura
- `src/darwin_heliobiology/` — núcleo fenomenológico (SolarAtlas, SolarPsychodynamics, serviços Kairos/Aletheia).
- `analysis/`, `dashboards/`, `clinical/`, `simulations/`, `manuscripts/` — entregas das sprints.
- `docs/` — roadmap, catálogo de datasets, data lake, ética.

Leia o manifesto completo em `README.exocortex`.

## Desenvolvimento
```bash
poetry install
poetry run pytest
poetry run black src
poetry run ruff src tests
poetry run mypy src
```

## Roadmap
Veja `docs/ROADMAP.md` para sprints e entregáveis.

## Licença
MIT.

## HelioMind Index
- Executar `poetry run python scripts/build_heliomind_index.py --dry-run` para visualizar a métrica.
- Usar `--output data/processed/heliomind_index.parquet` ou `.json/.csv` para persistir no data lake.
## HRV + Mood Pipeline
- Executar `scripts/ingest_wesad.py --skip-download --extract-to <dir> --output data/processed/hrv_mood_wesad.csv` para processar arquivos locais do WESAD.
- Ajustar parâmetros `--window-minutes` e `--min-samples` conforme necessidade (default 5min / 30 amostras).
- Especificações detalhadas em `docs/HRV_MOOD_SPEC.md`.

