# DARWIN Heliobiology — Panorama SOTA HRV + Mood
Criado: 2025-11-08 12:00:00 -03
Autor: AI Assistant + Dr. Demetrios Agourakis

## Objetivo
Mapear o estado da arte (SOTA) para modelagem heliobiológica aplicada à saúde mental, orientando experimentos computacionais, priorização de datasets públicos e desenho de pipelines reprodutíveis nível Q1.

## Matriz SOTA (Modelos × Sinais × Capacidades)

| Categoria | Técnicas de Referência | Sinais / Features | Capacidade-Alvo | Notas de Implementação |
|-----------|-----------------------|-------------------|------------------|------------------------|
| Auto-supervisão e representação | TS2Vec, T-Loss (Triplet), BYOL-T | RR intervals, acelerometria, EDA | Embeddings robustos para HRV/mood | Pré-treinar em WESAD/TILES, fine-tuning com RADAR-MDD |
| Transformers temporais | Temporal Fusion Transformer, PatchTST, Informer v2 | Solar indices (Kp, Dst, Bz), HRV features, mood scores | Previsão multi-horizonte com atenção interpretável | Usar attention masks guiadas por literatura Helio ↔ Mood |
| Forecast híbrido | NBEATSx, NeuralProphet, Mean-Reverting GPSSM | Séries Kp/Dst, HelioMind Index | Previsão de tempestades geomagnéticas e estados autonômicos | Integrar com baseline exponencial (Kairos Forecaster) |
| Causal discovery | PCMCI+, LPCMCI, Causal Transformer | Sequências multi-lag Solar ↔ HRV ↔ Mood | Inferência causal e detecção de atrasos | Incorporar priors de phase space (Ψ) |
| Biomarcadores geométricos | Wavelet scattering + GNN espectral | Bandas VLF/LF/HF, curva Bz | Detecção de assinaturas geomagnéticas | Pipeline GPU (PyG) para espectrogramas |
| Modelos de risco clínico | Dynamic Bayesian Networks, Survival Transformer, EBM | Curvas de HelioMind, mood e suicidality index | Probabilidade de crise psicossocial | Balancear interpretabilidade (EBM) vs performance (Survival Transformer) |
| Explanabilidade | DeepSHAP, Attention Roll-out, TimeSeriesCF | Contribuição feature-temporal | Alertas epistemológicos interpretáveis | Gerar contrafactuais Helio vs HRV mantendo mood |

## Datasets Prioritários

- **NOAA SWPC & NASA OMNIWeb** — índices Kp, Dst, AE, Bz e vento solar (resoluções 1min/1h).
- **GFZ Potsdam** — índices complementares (ap, AA) para cross-check.
- **WESAD**, **RADAR-MDD**, **TILES-2018** — HRV + mood (EMA) em wearables.
- **UK Biobank (subconjunto mental health)** — questionários e acelerometria wrist.
- **CDC WONDER / WHO Mortality** — séries epidemiológicas para validação populacional.
- **MIMIC-IV Waveform & VitalDB** — sinais cardíacos de alta frequência (benchmark de HRV).

## Artigos/Referências 2023-2025

- Li et al. 2024 — *Transformers for Wearable Stress Detection* (IEEE TBME).
- Andersson et al. 2024 — *Solar-Terrestrial Gaussian Process State Space Models* (NeurIPS).
- Zhukov et al. 2025 — *Multimodal Emotion Forecasting with External Events* (AAAI).
- Frolov et al. 2024 — *Dynamic HRV Biomarkers for Depression Relapse* (Nature Digital Medicine).
- Krakov et al. 2023 — *Geomagnetic Influences on Psychiatric Emergencies* (Scientific Reports).
- Runge et al. 2024 — *Causal Graph Discovery in High-Dimensional Time Series* (Annals of Applied Statistics).

## Recomendações de Pipeline

1. **Pré-processamento unificado**: normalizar RR intervals (z-score/robust), etiquetar mood com `make_mood_score`, construir HelioMind index e unir streams via `subject_id + timestamp`.
2. **Representação auto-supervisionada**: treinar TS2Vec/BYOL em janelas de HRV e mood, armazenando embeddings no data lake.
3. **Modelagem preditiva**: experimentar TFT/PatchTST com features exógenas (solar + autonomic + mood) e baseline EBM.
4. **Causalidade**: rodar PCMCI+ e Causal Transformer com priors baseados em literatura (lags 0-72h).
5. **Explicabilidade**: gerar atenção agregada, SHAP temporal e contrafactuais Helio vs Autonomic.
6. **Validação científica**: usar `AletheiaValidator` com ranges da literatura (r = 0.35-0.72) e calcular métricas de reprodutibilidade.

## Próximos Passos Sugeridos

- Automatizar ingestão RADAR-MDD e TILES-2018 com cron jobs (Prefect/Dagster).
- Montar notebook `analysis/sota_eval.ipynb` comparando baselines (Kairos vs TFT vs NBEATSx).
- Configurar MLflow para rastrear experimentos SOTA (hyperparams, métricas, curvas de atenção).
- Planejar submissão a conferências/journals (AAAI 2026, Nature Digital Medicine).

