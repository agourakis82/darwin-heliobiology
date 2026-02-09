# Scientific Foundations — DARWIN Heliobiology

**Status**: Living document — updated as new evidence emerges
**Last review**: 2026-02-09

> **Princípio diretor**: toda afirmação codificada neste projeto deve ser rastreável
> a uma publicação peer-reviewed, ou explicitamente marcada como **EXPLORATÓRIA**.
> Não queremos virar piada científica.

---

## Grau de Evidência — Legenda

| Grau | Significado | Requisito mínimo |
|------|-------------|-------------------|
| **A — FORTE** | Meta-análise ou estudo prospectivo de grande coorte (n > 500) com replicação | DOI + efeito replicado |
| **B — MODERADA** | Estudos observacionais com n razoável (50–500), mecanismo plausível | DOI + consistência entre estudos |
| **C — FRACA** | Estudos ecológicos, amostras pequenas (n < 50), sem replicação | DOI, mas viés alto ou sem replicação |
| **D — EXPLORATÓRIA** | Heurística do projeto sem suporte direto na literatura | Marcado explicitamente no código |

---

## 1. Efeitos Cardiovasculares da Atividade Geomagnética

### Grau: A — FORTE

A associação entre tempestades geomagnéticas e eventos cardiovasculares é a evidência
**mais robusta** no campo heliobiológico.

| Estudo | Design | n | Efeito principal | DOI |
|--------|--------|---|------------------|-----|
| Vencloviene et al. 2022 (meta-análise) | Revisão sistemática 38 estudos | >500k eventos | RR 1.04–1.18 para IAM durante alta atividade geomagnética | 10.3390/ijerph19031104 |
| Gaisenok et al. 2025 (revisão) | Revisão narrativa de múltiplos estudos | Milhares | RR 1.3–1.5 para SCA durante tempestades | PMC12005662 |
| Stoupel et al. 2006 | Coorte retrospectiva 1999–2003 | 3,742 mortes cardíacas | Correlação com atividade cósmica neutron monitor | 10.1016/j.ijcard.2005.10.011 |

**Implicação para o código**: O HelioMind Index pode legitimamente associar alta atividade
geomagnética (Kp, Dst) a risco cardiovascular elevado. Pesos no índice composto devem
refletir a magnitude real do efeito (RR ~1.1, **não** dobrando o risco).

---

## 2. HRV e Atividade Geomagnética

### Grau: B — MODERADA

| Estudo | Design | n | Efeito principal | DOI |
|--------|--------|---|------------------|-----|
| Ong et al. 2022 (Normative Aging Study) | Coorte prospectiva, medidas repetidas | 809 homens | Kp ↑ IQR → RMSSD -14.7ms (95% CI: -23.1, -6.3; p=0.0007), SDNN -8.2ms (p=0.006) | PMC9233046 |
| Alabdulgader & McCraty 2018 | Longitudinal 72h × 16 participantes | 16 | Correlação Kp–HRV, mas autocorrelação não corrigida | 10.1038/s41598-018-20932-x |
| Cornelissen et al. 2002 | Monitoramento contínuo | 100 (estimativa) | Variação circadiana HRV sincronizada com campo geomagnético | 10.1081/CBI-120005403 |

**Pontos fortes**: Ong et al. 2022 é o estudo de mais alta qualidade disponível —
coorte grande (n=809), medidas repetidas, controle de confounders (temperatura,
poluição, sazonalidade).

**Pontos fracos**: Alabdulgader/McCraty tem n=16 e não corrige autocorrelação temporal
— seus efeitos são provavelmente superestimados. Não deve ser citado como evidência
primária.

**Implicação para o código**:
- `psychophysiology.py:normalized_sensitivity()` usa RMSSD/100 como normalização.
  Baseado em Ong et al., a faixa normativa de RMSSD em homens adultos é ~20–60ms.
  A divisão por 100 é uma heurística razoável, mas deve ser documentada como tal.
- O efeito real de Kp sobre RMSSD é ~15ms por IQR de Kp. Isso é **clinicamente
  modesto** — não justifica alertas de "crise" por si só.

---

## 3. Saúde Mental, Suicídio e Atividade Geomagnética

### Grau: C — FRACA

| Estudo | Design | n | Efeito principal | DOI |
|--------|--------|---|------------------|-----|
| Gordon & Berk 2003 | Ecológico (correlação temporal) | Séries populacionais | r = 0.69 suicídio × atividade geomagnética (agregado anual) | (South African J. Psychiatry) |
| Berk et al. 2006 | Ecológico, 1968–2002 | Séries populacionais Austrália | Efeito apenas em mulheres no outono; sem efeito geral | 10.1002/bem.20190 |
| Kay 1994 | Ecológico, hospital único | Registros UK | +36.2% admissões masculinas durante tempestades | 10.1192/bjp.164.3.403 |

**Problemas fundamentais**:
1. **Falácia ecológica**: Correlações populacionais não implicam efeito individual.
2. **Confounding sazonal**: Suicídio tem pico sazonal (primavera) que co-varia com
   atividade solar. Gordon & Berk 2003 não controlam sazonalidade → r = 0.69 é
   **provavelmente espúrio**.
3. **Não replicação**: Kay 1994 nunca foi replicado. Berk 2006 mostra efeito apenas
   em subgrupo (mulheres, outono) — marca registrada de p-hacking ou acaso.
4. **Viés de publicação**: Estudos negativos não são publicados neste campo.

**Implicação para o código**:
- `ScientificExpectation(lower=0.3, upper=0.8)` para "Geomag vs. suicídio" é
  **injustificável**. A faixa real, se existir efeito, é r = 0.05–0.20 em dados
  individuais (não ecológicos).
- O `suicidality_index` no phase_space.py deve ser tratado como **hipotético**.
  O threshold de 0.6 em ONTOLOGY.md não tem fundamento em literatura.
- Alertas CRITICAL combinando Kp+suicidality devem ser marcados como exploratórios.

---

## 4. Mecanismos Biofísicos Propostos

### Grau: C — FRACA (mecanismo plausível, sem prova em humanos)

| Mecanismo | Evidência | Referência |
|-----------|-----------|------------|
| Criptocromo (magnetorrecepção) | Demonstrado em aves e insetos; humano Cry2 responde in vitro | Close et al. 2012 (PMC3321722), Foley et al. 2011 |
| Melatonina/pineal | Hipótese de supressão da melatonina por campos magnéticos; dados inconsistentes em humanos | Burch et al. 1999 (10.1016/S0197-4580(99)00043-1) |
| Schumann resonances e ritmos cerebrais | Sobreposição de frequências (7.83 Hz ≈ theta/alpha); correlação especulativa | Cherry 2002 (não peer-reviewed), Saroka et al. 2014 |

**Avaliação honesta**: Nenhum mecanismo proposto foi **comprovado** em humanos sob
condições controladas. A plausibilidade do criptocromo é a mais forte, mas a
translação ave→humano é incerta. A hipótese melatonina tem dados conflitantes.
Schumann resonances é a mais especulativa e tangencia pseudociência.

---

## 5. Constantes e Limiares no Código — Rastreabilidade

### 5.1 helio_index.py — Pesos do Índice Composto

```python
# Pesos atuais (EXPLORATÓRIO — sem base empírica direta)
0.35 * kp_activity        # Kp é o preditor mais estudado → peso maior
0.25 * dst_storm_intensity # Dst mede intensidade de tempestade
0.20 * bz_reconnection    # Bz sul permite reconexão magnética
0.15 * solar_wind_pressure # Pressão dinâmica, efeito menos direto
0.05 * variability         # Flutuação, efeito sub-explorado
```

**Status**: D — EXPLORATÓRIA. A ordenação relativa (Kp > Dst > Bz > vento > variabilidade)
é consistente com a literatura (Kp é mais usado em estudos epidemiológicos), mas os
valores numéricos exatos não derivam de nenhum estudo. São pesos arbitrários que
**precisam ser calibrados empiricamente** (e.g., via regressão logística sobre desfechos
clínicos, se disponíveis).

### 5.2 helio_index.py — Constantes de Normalização

| Constante | Valor | Justificativa |
|-----------|-------|---------------|
| Kp / 9.0 | Escala Kp vai de 0 a 9 | **CORRETO** — escala oficial NOAA |
| Dst / 300.0 | Dst extremo ≈ -300 nT (Bastille Day 2000: -301 nT) | **RAZOÁVEL** — baseado em eventos históricos extremos |
| Bz / 20.0 | Bz extremo ≈ -20 nT em tempestades severas | **RAZOÁVEL** — eventos G4/G5 atingem -15 a -25 nT |
| Pressão / 300,000 | ρv² normalizado | **EXPLORATÓRIO** — sem referência direta |
| Variabilidade / 2.5 | std(Kp)/2.5 | **EXPLORATÓRIO** — threshold arbitrário |

### 5.3 helio_index.py — Limiares de Alerta

| Limiar | Valor | Justificativa |
|--------|-------|---------------|
| `kp_activity >= 0.7` | Kp ≥ 6.3 | Kp ≥ 7 = G3 (forte) pela NOAA. 0.7 × 9 = 6.3 → aproxima G3. **RAZOÁVEL.** |
| `dst_storm_intensity >= 0.6` | Dst ≤ -180 nT | Dst < -200 nT = tempestade severa. **RAZOÁVEL.** |
| `bz_reconnection >= 0.5` | Bz ≤ -10 nT | Bz < -10 nT favorece reconexão significativa. **RAZOÁVEL.** |
| `variability >= 0.6` | std(Kp) ≥ 1.5 | **EXPLORATÓRIO** — sem referência |

### 5.4 phase_space.py — Limiares de Alerta Epistêmico

| Condição | Status |
|----------|--------|
| `kp >= 6 AND suicidality >= 0.4` → CRITICAL | **D — EXPLORATÓRIA.** Não existe estudo que associe Kp individual a risco suicida individual. |
| `dst <= -50 AND HRV < 50` → ALTA TENSÃO | **C — FRACA.** Dst < -50 é tempestade moderada (NOAA). HRV < 50ms é baixa (Shaffer & Ginsberg 2017). A combinação é plausível mas não testada. |
| `circadian_shift >= 2h AND mood <= 0.3` → DISRUPÇÃO | **B — MODERADA.** Disrupção circadiana + humor baixo é bem documentada na psiquiatria do sono (Walker 2017). Mas a associação com atividade geomagnética é especulativa. |

### 5.5 psychophysiology.py — normalized_sensitivity()

```python
baseline = max(rmssd_ms, 1.0)
scale = 1 - (baseline / 100.0)  # RMSSD ~20-60ms normal → scale ~0.4-0.8
circadian_penalty = (sdnn_ms - 50) / 100.0  # SDNN ~30-100ms normal
return scale + circadian_penalty * 0.2
```

**Status**: D — EXPLORATÓRIA. A intuição (menor RMSSD → maior sensibilidade) é
consistente com Ong et al. 2022, mas a fórmula exata é heurística sem validação.
**Nota**: A função `passport_risk_adjustment()` em `services/passport.py` substitui
esta heurística por coeficientes aprendidos de dados longitudinais — preferir passport.

---

## 6. O que NÃO Devemos Afirmar

1. **"Tempestades solares causam suicídio"** → Não há evidência causal. Estudos são
   ecológicos e confundidos por sazonalidade.

2. **"HRV prediz risco psiquiátrico durante tempestades"** → HRV diminui ~15ms durante
   alta atividade geomagnética (Ong 2022). Isso é estatisticamente significativo mas
   **clinicamente modesto**. Não é "predição de risco".

3. **"O campo magnético terrestre controla o humor"** → Alegação sem mecanismo
   comprovado. O efeito, se existir, é pequeno e modulado por dezenas de confounders.

4. **"Schumann resonances sincronizam ondas cerebrais"** → Especulação sem evidência
   robusta. Não usar em publicações ou comunicação pública.

5. **"Nosso índice HelioMind prevê crises de saúde mental"** → O índice é um score
   composto exploratório. Seus pesos não foram calibrados contra desfechos clínicos.

---

## 7. Recomendações para Publicação

1. **Framework, não afirmação**: Posicionar o projeto como framework computacional
   para investigar correlações sol-mente, **não** como sistema de predição clínica.

2. **Calibração empírica necessária**: Antes de publicar, os pesos do HelioMind Index
   devem ser calibrados contra dados clínicos reais (e.g., admissões psiquiátricas
   × índices solares).

3. **Transparência epistêmica**: Todo paper deve incluir tabela de evidência com
   graus A–D, como este documento.

4. **Pre-registration**: Registrar hipóteses em OSF/AsPredicted antes de rodar análises
   para evitar HARKing.

5. **Alvo de publicação realista**: Frontiers in Psychiatry, International Journal
   of Biometeorology, ou similar. Nature/AAAI seria prematuro sem calibração clínica.

---

## Referências Completas

1. Berk M, Dodd S, Henry M. Do ambient electromagnetic fields affect behaviour?
   A demonstration of the relationship between geomagnetic storm activity and
   suicide. *Bioelectromagnetics*. 2006;27(2):151-155. doi:10.1002/bem.20190

2. Burch JB, Reif JS, Yost MG. Geomagnetic disturbances are associated with
   reduced nocturnal excretion of a melatonin metabolite in humans. *Neurosci Lett*.
   1999;266(3):209-212. doi:10.1016/S0304-3940(99)00308-0

3. Close J, Sherwood K, Sherwood B, et al. The radical pair mechanism of
   magnetoreception: cryptochrome-based magnetoreception in animals. *Ann Rev Biophys*.
   2012. PMC3321722

4. Cornelissen G, Halberg F, Breus T, et al. Non-photic solar associations of heart
   rate variability and myocardial infarction. *J Atmos Sol-Terr Phys*.
   2002;64(5-6):707-720. doi:10.1081/CBI-120005403

5. Gaisenok OV, et al. Geomagnetic activity and cardiovascular disease: a review
   of recent evidence. 2025. PMC12005662

6. Gordon C, Berk M. The effect of geomagnetic storms on suicide.
   *S Afr Psychiatry Rev*. 2003;6:24-27.

7. Kay RW. Geomagnetic storms: association with incidence of depression as measured
   by hospital admission. *Br J Psychiatry*. 1994;164(3):403-409.
   doi:10.1192/bjp.164.3.403

8. Alabdulgader A, McCraty R, et al. Long-term study of heart rate variability
   responses to changes in the solar and geomagnetic environment.
   *Sci Rep*. 2018;8:2663. doi:10.1038/s41598-018-20932-x

9. Ong KM, et al. Geomagnetic activity and heart rate variability in the
   Normative Aging Study. *Environ Health Perspect*. 2022. PMC9233046

10. Shaffer F, Ginsberg JP. An overview of heart rate variability metrics and norms.
    *Front Public Health*. 2017;5:258. doi:10.3389/fpubh.2017.00258

11. Stoupel E, et al. Clinical cosmobiology — sudden cardiac death and daily/monthly
    geomagnetic, cosmic ray and solar activity: the Baku study 1999–2003.
    *Int J Cardiol*. 2006;108(3):423-424. doi:10.1016/j.ijcard.2005.10.011

12. Vencloviene J, et al. The effect of geomagnetic storms on the risk of acute
    myocardial infarction: a systematic review and meta-analysis. *Int J Environ
    Res Public Health*. 2022;19(3):1104. doi:10.3390/ijerph19031104
