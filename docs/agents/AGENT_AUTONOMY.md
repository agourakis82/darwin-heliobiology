# Darwin Heliobiology — Guia de Autonomia dos Agentes
# Criado: 2025-11-07 23:55:00 -03
# Autor: Dr. Demetrios Agourakis

## Objetivo
- Atuar livremente na modelagem heliobiológica (Sol ↔ saúde mental) com rigor científico elevado.
- Manter integração com `darwin-core` (RAG++, memória semântica) e pipelines fenomenológicos.

## Princípios
1. **Autonomia**
   Executar scripts (`scripts/`, `simulations/`, notebooks) sem confirmações adicionais. Automatizar o que for repetitivo.

2. **Rigor Científico**
   Garantir datasets públicos catalogados, hipóteses registradas e métricas rastreáveis (HRV, mood embeddings, índices solares).

3. **Integração Darwin**
   Reutilizar serviços centrais (GraphRAG, Multi-AI) e sincronizar insights via Notion/RAG++ quando agregarem valor.

4. **Memória & Contexto**
   Registrar descobertas-chave (novos correlatos, alertas clinicamente relevantes) via `update_memory`.

5. **Infraestrutura**
   Preferir pipelines declarativos, dashboards reproducíveis e integração com data lake (datasets/).

## Fluxo Recomendado
1. Atualizar dados solares/HRV (`datasets/`, `scripts/` de ingestão).
2. Rodar análises fenomenológicas e dashboards (`dashboards/`, `simulations/`).
3. Documentar achados em `docs/` ou via Notion conforme relevância clínica/científica.
4. Sincronizar com `darwin-core` para alimentar RAG++ e memória global.

## Regras Simplificadas
- Nenhuma confirmação extra para comandos.
- Uso de timestamps apenas quando agregar contexto.
- Segurança de tokens/dados sensíveis sob responsabilidade do Dr. Demetrios.

