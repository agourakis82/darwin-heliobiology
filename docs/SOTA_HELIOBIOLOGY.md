# DARWIN Heliobiology — Panorama SOTA HRV + Mood

Criado: 2025-11-08 12:00:00 -03
Autor: AI Assistant + Dr. Demetrios Agourakis
Revisado: 2026-02-09 (adição de DOIs verificados e gradação de evidência)

> **Nota**: Para avaliação crítica da base científica, ver
> [docs/SCIENTIFIC_FOUNDATIONS.md](SCIENTIFIC_FOUNDATIONS.md).

## Objetivo

Mapear o estado da arte (SOTA) para modelagem heliobiológica aplicada à saúde mental,
orientando experimentos computacionais, priorização de datasets públicos e desenho de
pipelines reprodutíveis nível Q1.

## Matriz SOTA (Modelos x Sinais x Capacidades)

| Categoria | Técnicas de Referência | Sinais / Features | Capacidade-Alvo | Notas de Implementação |
|-----------|-----------------------|-------------------|------------------|------------------------|
| Auto-supervisão e representação | TS2Vec, T-Loss (Triplet), BYOL-T | RR intervals, acelerometria, EDA | Embeddings robustos para HRV/mood | Pré-treinar em WESAD/TILES, fine-tuning com RADAR-MDD |
| Transformers temporais | Temporal Fusion Transformer, PatchTST, Informer v2 | Solar indices (Kp, Dst, Bz), HRV features, mood scores | Previsão multi-horizonte com atenção interpretável | Usar attention masks guiadas por literatura Helio - Mood |
| Forecast híbrido | NBEATSx, NeuralProphet, Mean-Reverting GPSSM | Séries Kp/Dst, HelioMind Index | Previsão de tempestades geomagnéticas e estados autonômicos | Integrar com baseline exponencial (Kairos Forecaster) |
| Causal discovery | PCMCI+, LPCMCI, Causal Transformer | Sequências multi-lag Solar - HRV - Mood | Inferência causal e detecção de atrasos | Incorporar priors de phase space |
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

## Referências com DOIs Verificados

### Evidência Forte (Grau A) — Cardiovascular

| Ref | Estudo | DOI / ID | Achado Principal |
|-----|--------|----------|------------------|
| 1 | Vencloviene et al. 2022 — Meta-análise IAM + atividade geomagnética | doi:10.3390/ijerph19031104 | RR 1.04–1.18 para IAM durante alta atividade geomag |
| 2 | Gaisenok et al. 2025 — Revisão cardiovascular | PMC12005662 | RR 1.3–1.5 para SCA durante tempestades |
| 3 | Stoupel et al. 2006 — Mortalidade cardíaca Baku | doi:10.1016/j.ijcard.2005.10.011 | Correlação com atividade cósmica neutron monitor |

### Evidência Moderada (Grau B) — HRV e Geomagnetismo

| Ref | Estudo | DOI / ID | Achado Principal |
|-----|--------|----------|------------------|
| 4 | Ong et al. 2022 — Normative Aging Study (n=809) | PMC9233046 | Kp ↑ IQR → RMSSD -14.7ms (p=0.0007) |
| 5 | Alabdulgader & McCraty 2018 — HRV longitudinal 72h | doi:10.1038/s41598-018-20932-x | Correlação Kp-HRV (n=16, autocorrelação não corrigida) |
| 6 | Cornelissen et al. 2002 — Variação circadiana HRV | doi:10.1081/CBI-120005403 | Ritmos HRV sincronizados com campo geomagnético |

### Evidência Fraca (Grau C) — Saúde Mental / Suicídio

| Ref | Estudo | DOI / ID | Achado Principal |
|-----|--------|----------|------------------|
| 7 | Berk et al. 2006 — Suicídio e geomagnetismo | doi:10.1002/bem.20190 | Efeito apenas em mulheres no outono; sem efeito geral |
| 8 | Gordon & Berk 2003 — Suicídio e tempestades | S Afr Psychiatry Rev, 6:24-27 | r=0.69 (agregado anual, confundido por sazonalidade) |
| 9 | Kay 1994 — Admissões psiquiátricas e tempestades | doi:10.1192/bjp.164.3.403 | +36.2% admissões masculinas (não replicado) |

### Mecanismos Propostos (Grau C — plausíveis mas não provados em humanos)

| Ref | Estudo | DOI / ID | Achado Principal |
|-----|--------|----------|------------------|
| 10 | Close et al. 2012 — Criptocromo e magnetorrecepção | PMC3321722 | Cry2 humano responde in vitro; translação incerta |
| 11 | Burch et al. 1999 — Melatonina e campo magnético | doi:10.1016/S0304-3940(99)00308-0 | Supressão melatonina — dados inconsistentes |

### Normas HRV

| Ref | Estudo | DOI / ID | Relevância |
|-----|--------|----------|------------|
| 12 | Shaffer & Ginsberg 2017 — HRV metrics and norms | doi:10.3389/fpubh.2017.00258 | RMSSD normal ~20-60ms; normas etárias |

### Metodologia SOTA — Séries Temporais e Causalidade

| Ref | Estudo | DOI / ID | Relevância |
|-----|--------|----------|------------|
| 13 | Runge et al. 2019 — PCMCI+ | doi:10.1126/sciadv.aau4996 | Framework causal para séries temporais com lags |
| 14 | Lim et al. 2021 — Temporal Fusion Transformers | doi:10.1016/j.ijforecast.2021.03.012 | Forecast multi-horizonte interpretável |

## Recomendações de Pipeline

1. **Pré-processamento unificado**: normalizar RR intervals (z-score/robust), etiquetar mood com `make_mood_score`, construir HelioMind index e unir streams via `subject_id + timestamp`.
2. **Representação auto-supervisionada**: treinar TS2Vec/BYOL em janelas de HRV e mood, armazenando embeddings no data lake.
3. **Modelagem preditiva**: experimentar TFT/PatchTST com features exógenas (solar + autonomic + mood) e baseline EBM.
4. **Causalidade**: rodar PCMCI+ e Causal Transformer com priors baseados em literatura (lags 0-72h).
5. **Explicabilidade**: gerar atenção agregada, SHAP temporal e contrafactuais Helio vs Autonomic.
6. **Validação científica**: usar `AletheiaValidator` com ranges da literatura — r_individual = 0.05–0.25 para efeitos geomag-HRV (Ong 2022); r_ecológico = 0.30–0.70 apenas para séries agregadas (não usar como expectativa individual).

## Próximos Passos Sugeridos

- Automatizar ingestão RADAR-MDD e TILES-2018 com cron jobs (Prefect/Dagster).
- Montar notebook `analysis/sota_eval.ipynb` comparando baselines (Kairos vs TFT vs NBEATSx).
- Configurar MLflow para rastrear experimentos SOTA (hyperparams, métricas, curvas de atenção).
- **Calibrar pesos HelioMind Index** contra desfechos clínicos antes de publicar.
- Pre-registrar hipóteses em OSF/AsPredicted para evitar HARKing.
- Alvo de publicação realista: Frontiers in Psychiatry, Int J Biometeorology, ou similar.
