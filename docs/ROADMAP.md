# DARWIN Heliobiology — Roadmap

## Sprint S0 — Bootstrap (2 dias)
- [ ] Exportar pacote inicial
- [ ] Configurar Poetry + dependências
- [ ] Configurar CI (lint, mypy, pytest, coverage)
- [ ] Criar doc `DATASET_CATALOG.md`

## Sprint S1 — HelioMind Index & Biomarkers (5 dias)
- [x] Construir `HelioMind Index` (ingestão NOAA/NASA, API, dashboard)
- [x] Pipeline HRV + mood com datasets públicos
- [x] Panorama SOTA heliobiologia (ver `docs/SOTA_HELIOBIOLOGY.md`)
- [ ] Documentar `HELIOBIOLOGY_DATA_LAKE.md`

## Sprint S2 — Atlas, Passaporte e Metaanálise (6 dias)
- [ ] Atlas temporal de assinaturas geomagnéticas
- [ ] Passaporte psico-geomagnético (personalização)
- [ ] Motor `Aletheia` para metaanálise automatizada
- [ ] Pipeline TFT/PatchTST com features HelioMind + HRV
- [ ] Rodar PCMCI+ com priors Helio ↔ Mood

## Sprint S3 — Clínica, Simulação e Publicação (7 dias)
- [ ] Carta clínica heliobiológica (SOAP auto)
- [ ] Simulações agent-based de intervenções
- [ ] RAG++ automatizado e Insight Log
- [ ] Manuscritos + preprint + vídeo demo

## Guias rápidos
- **Issues**: uma por deliverable (HelioMind, HRV, Atlas, etc.)
- **Branches**: `feature/s1-helio-index`, `feature/s2-atlas`...
- **Padrões**: SemVer, CHANGELOG, testes ≥85%, docstrings com carimbo editorial.
