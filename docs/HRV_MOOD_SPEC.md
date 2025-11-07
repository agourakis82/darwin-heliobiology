# Especificação — Pipeline HRV + Mood

## Objetivos
- Integrar séries autonômicas (RR/HRV) com autorrelatos de humor/estresse usando apenas datasets públicos.
- Produzir features normalizadas e prontas para modelagem (previsão multimodal, correlações com HelioMind Index).
- Garantir reprodutibilidade e versionamento do data lake.

## Datasets Prioritários
| Conjunto | Modalidade | Conteúdo | Licença |
| --- | --- | --- | --- |
| WESAD (U. Siegen) | Wearable (ECG/EDA) + rótulos affectivos | Sinais fisiológicos brutos + estados baseline/stress | Uso acadêmico, requer aceite | 
| TILES-2018 | Wearable Empatica E4 + EMA (PANAS) | HR, HRV derivados, escalas diárias | DUA | 
| RADAR-MDD | PPG smartphone + PHQ-8/9 | Mood longitudinal + sinais PPG | Acesso controlado | 
| Open Wearables (Zenodo) | PPG/ECG curtos + anotações | HRV de dispositivos de consumo | CC | 

> MVP inicial: ingestão WESAD + referência sintética (fixtures) para validar o pipeline.

## Métricas HRV (Suportadas no MVP)
- RMSSD, SDNN, pNN50, média/mediana HR.
- Índices de frequência (LF/HF) — placeholder para iteração futura.
- Sample Entropy (entropia aproximada) com fallback para sequências curtas.

## Normalização de Humor
- Escalas Likert → faixa [0, 1] (min–max por questionário).
- Fusão de múltiplas escalas via média ponderada (PANAS, PHQ, stress label → score único).
- Discretização opcional (`estavel`, `vigilancia`, `alerta`).

## Esquema de Saída
Arquivo `data/processed/hrv_mood_features.parquet` com colunas:
```
subject_id | timestamp | window_minutes | hrv_rmssd | hrv_sdnn | hrv_pnn50 |
hr_mean | entropy | mood_score | mood_label | dataset | meta_version
```

## Requisitos Técnicos
- Resample fixo (30, 60 minutos) com janelas rolantes.
- Logs estruturados (`logging`) durante ingestão.
- Testes unitários com dados sintéticos (RR intervalos gerados + mood mock).
- Integração opcional com HelioMind Index numa segunda etapa.

## Roadmap Técnico
1. Funções de features HRV (`src/darwin_heliobiology/features/hrv.py`).
2. Normalização de mood (`src/darwin_heliobiology/preprocessing/mood.py`).
3. Pipeline de agregação (`src/darwin_heliobiology/pipelines/hrv_mood.py`).
4. Scripts CLI (`scripts/build_hrv_mood_pipeline.py`) [futuro].
5. Notebooks de exploração (`analysis/`).

## Referências
- Task Force of ESC/NASPE, "Heart rate variability: standards of measurement" (1996).
- Can et al., WESAD dataset (2019).
- Recent SOTA: Temporal Fusion Transformers, TimesNet para previsão multimodal.
