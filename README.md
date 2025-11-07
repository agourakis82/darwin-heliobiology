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
