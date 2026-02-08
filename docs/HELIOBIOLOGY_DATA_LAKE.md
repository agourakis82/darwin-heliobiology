# Data Lake Heliobiológico

## Estrutura de diretórios
```
./data/
  raw/
    noaa/
    nasa_omni/
    who/
  interim/
    heliomind_index/
    hrv_mood/
  processed/
    atlas/
    passport/
```

## Pipeline de ingestão
1. `scripts/fetch_noaa.py` — baixa e cacheia índices Kp/Dst/Bz/vento solar via `SolarAtlas` (Parquet/CSV/JSON).
2. `scripts/fetch_omni.py` — baixa dados OMNI2 hourly (NASA SPDF) em formato fixed-width e converte para Parquet/CSV.
3. `scripts/fetch_who.py` — baixa e extrai ZIPs de mortalidade WHO (ICD-10 + população) para CSVs locais.
4. `scripts/build_heliomind_index.py` — calcula o HelioMind Index a partir de dados NOAA e exporta (Parquet/JSON/CSV).
5. `scripts/ingest_wesad.py` — baixa e processa o dataset WESAD gerando features HRV + mood.
6. `scripts/build_hrv_mood_pipeline.py` — pipeline genérico: qualquer CSV com RR intervals → features HRV + mood.

## Controles de qualidade
- Checksums e versões dos datasets (registrar em `data/VERSIONS.md`).
- Logs estruturados (timestamp, fonte, status HTTP).
- Retenção: manter raw completo; processed apenas últimos 3 meses (com reprocessamento automatizado).

## Próximos passos
- Automatizar ingestão com GitHub Actions (cron semanal).
- Criar `docs/ETHICS_COMPLIANCE.md` com termos de uso por dataset.
