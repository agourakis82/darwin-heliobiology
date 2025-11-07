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
1. `scripts/fetch_noaa.py` — baixa e cacheia índices Kp/Dst/Bz (JSON → Parquet).
2. `scripts/fetch_omni.py` — dados do OMNIWeb via REST.
3. `scripts/fetch_who.py` — extrai tabelas WHO mortality (CSV).
4. `scripts/build_heliomind_index.py` — compõe métricas e salva em `processed/heliomind_index.parquet`.

## Controles de qualidade
- Checksums e versões dos datasets (registrar em `data/VERSIONS.md`).
- Logs estruturados (timestamp, fonte, status HTTP).
- Retenção: manter raw completo; processed apenas últimos 3 meses (com reprocessamento automatizado).

## Próximos passos
- Automatizar ingestão com GitHub Actions (cron semanal).
- Documentar termos de uso específicos (ver `docs/ETHICS_COMPLIANCE.md`).
