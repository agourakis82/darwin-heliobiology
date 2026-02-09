# Ética e Compliance — DARWIN Heliobiology

**Última revisão**: 2026-02-09

## 1. Princípio Fundamental

Este projeto opera exclusivamente com **dados públicos e abertos**.
Nenhum dado individual é coletado, processado ou armazenado sem que provenha
de datasets já publicados e disponíveis para pesquisa.

## 2. Fontes de Dados e Governança

| Dataset | Provedor | Licença / Termos | Dados pessoais? |
|---------|----------|------------------|-----------------|
| NOAA SWPC (Kp, Dst, solar wind) | NOAA / US Government | Domínio público | Não |
| NASA OMNIWeb (OMNI2 hourly) | NASA GSFC | Domínio público | Não |
| WESAD | UCI ML Repository | CC BY 4.0 | Sim — pseudonimizado (S2-S17) |
| WHO Mortality Database | WHO | Open access | Não — dados agregados populacionais |
| GFZ Potsdam (ap, AA) | GFZ German Research Centre | Open data | Não |

### WESAD — Considerações Especiais

- O dataset WESAD (Schmidt et al. 2018) contém sinais fisiológicos de 15 sujeitos.
- Os dados são pseudonimizados (identificadores S2–S17).
- A coleta original foi aprovada por comitê de ética (detalhes no paper original).
- Nosso uso é secundário e limitado a extração de features HRV agregadas.
- **Não tentamos re-identificar sujeitos.**

## 3. IRB e Comitê de Ética

Como o projeto usa **exclusivamente dados secundários já publicados**, não é
necessário submissão a IRB/CEP para as análises computacionais atuais.

**Se o projeto evoluir para coleta de dados primários** (e.g., estudo prospectivo
com wearables + questionários de humor), será obrigatório:
1. Submissão ao CEP/IRB da instituição responsável
2. TCLE (Termo de Consentimento Livre e Esclarecido) para participantes
3. Registro do estudo em plataforma pública (ClinicalTrials.gov ou Registro Brasileiro)
4. Plano de gerenciamento de dados conforme LGPD/GDPR

## 4. Riscos Éticos Identificados

### 4.1 Alegações Científicas Prematuras

**Risco**: Afirmar causalidade Sol→saúde mental sem evidência suficiente.

**Mitigação**:
- Toda constante no código é classificada por grau de evidência (A–D),
  conforme `docs/SCIENTIFIC_FOUNDATIONS.md`.
- Alertas no phase_space.py marcados como "EXPLORATÓRIO" quando baseados em
  evidência fraca.
- O projeto se posiciona como **framework computacional para investigação**,
  não como sistema de predição clínica.

### 4.2 Suicidality Index

**Risco**: Tratar suicidality como variável computável sem validação clínica.

**Mitigação**:
- O `suicidality_index` no phase_space.py representa um placeholder para
  escalas clínicas validadas (e.g., Columbia-Suicide Severity Rating Scale).
- **Não é usado para tomada de decisão clínica.**
- O threshold de singularidade (suicidality ≥ 0.6) foi removido do ONTOLOGY.md
  por falta de base empírica.

### 4.3 Determinismo Ambiental

**Risco**: Sugerir que fatores solares determinam comportamento humano, removendo
agência individual e contribuindo para estigma.

**Mitigação**:
- Documentação explicita que efeitos observados são **estatisticamente modestos**
  (RR ~1.1 para cardiovascular, ~15ms RMSSD para HRV).
- O projeto investiga correlações, não relações determinísticas.
- Comunicação pública (se houver) deve enfatizar a natureza exploratória.

## 5. LGPD / GDPR Compliance

| Requisito | Status |
|-----------|--------|
| Base legal para tratamento | Legítimo interesse em pesquisa (Art. 7, XI LGPD) |
| Dados pessoais sensíveis | Apenas via WESAD (pseudonimizado, uso secundário) |
| Transferência internacional | Dados NASA/NOAA = domínio público, sem restrição |
| Direito ao esquecimento | N/A — não coletamos dados diretamente |
| DPO / Encarregado | N/A para fase atual (pesquisa acadêmica) |

## 6. Checklist para Publicação

Antes de submeter qualquer paper baseado neste projeto:

- [ ] Verificar que todas as constantes citadas têm grau de evidência documentado
- [ ] Não fazer alegações causais sem evidência causal (e.g., PCMCI+ com lags)
- [ ] Incluir limitações: tamanho amostral, viés ecológico, confounders sazonais
- [ ] Declarar conflitos de interesse
- [ ] Citar fontes de dados com DOIs/URLs corretos
- [ ] Registrar hipóteses em OSF/AsPredicted antes de análises confirmatórias
- [ ] Disponibilizar código e dados processados para reprodutibilidade
