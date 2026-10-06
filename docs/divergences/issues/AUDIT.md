## Resumo
Auditoria de `stdlib/heliobiology/` (somente leitura; nenhum arquivo do stdlib foi editado). `effects.sio` tem coeficientes sem fonte e incertezas fixas proporcionais ao valor; `constants.sio` está desabilitado (1 linha) e `mod.sio` só exporta `heliobiology_module_ready()`. Isso importa porque o núcleo do darwin-heliobiology em Sounio (ADR-008/009) usa constantes calibradas e fontes graduadas (A–D) e este módulo não conversa com elas.

Fontes: tudo que está citado abaixo como "fonte disponível" vem de `docs/SCIENTIFIC_FOUNDATIONS.md` do repositório `agourakis82/darwin-heliobiology` (graus A–D). Onde digo **não encontrei fonte** significa: não há referência no arquivo nem nesse documento. Sugestões de correção são propostas, não verificadas contra os artigos (marcado "verificar").

## Constantes sem referência — `stdlib/heliobiology/effects.sio`

| linha | constante | valor | situação | correção sugerida |
|---|---|---|---|---|
| 31 | `kp_coeff` (RR de IAM por unidade de Kp acima de 4) | `0.03` | **sem fonte**. Cabeçalho cita Cornelissen 2002, Palmer 2006, Vencloviene 2014 sem ligar nenhuma a este valor | Substituir o modelo linear por RR categórico com IC da meta-análise de Vencloviene et al. 2022 (RR 1.04–1.18 para IAM em alta atividade geomagnética, doi 10.3390/ijerph19031104, grau A/B no documento) ou ajustar `kp_coeff` para reproduzir esse intervalo no limiar usado (verificar a definição de "alta atividade" do estudo). Citar o DOI no comentário. |
| 32 | `dst_coeff` | `0.01` | **não encontrei fonte** | Remover ou rotular "exploratório (grau D)" até haver fonte; não combinar multiplicativamente com `kp_effect` sem evidência de independência. |
| 33 | `lag_hours` | `24.0` | campo do struct nunca é lido por `cv_mi_risk` | Ou usar (atraso entre exposição e desfecho) com fonte, ou remover. |
| 46, 51 | limiares `kp >= 5.0` e `dst < -30` | `5.0`, `-30` | Kp ≥ 5 coincide com G1 (NOAA); `-30 nT` coincide com o limiar "weak" de `classify_dst` em `indices.sio:46-48`, que também **não cita fonte** | Documentar a origem de cada limiar (indices.sio inclusive). |
| 56 | incerteza do RR | `rr * 0.15` (15 % fixo) | **sem fonte**; é proporcional ao valor | Derivar do IC da meta-análise (ex.: meia-largura do IC de 1.04–1.18) ou propagar via `Knowledge<f64>` com a variância da fonte, não por fração fixa. |
| 62-63 | derrame: `0.6`, `0.4`, incerteza `× 0.6` | — | **sem fonte** ("weaker association" no comentário) | Citar estudo de AVC ou remover a função. |
| 73 | `baseline_sdnn` / `reduction_per_kp` | `140.0` ms / `3.0` ms por Kp | `140` é compatível com a faixa 24 h publicada pela Task Force ESC/NASPE 1996 (SDNN 141 ± 39 ms; **verificar**); `3.0 ms/Kp` **não encontrei fonte** | O efeito publicado no documento é Ong et al. 2022: aumento de 1 IQR de Kp → RMSSD −14.7 ms (IC95 −23.1, −6.3), SDNN −8.2 ms (p=0.006) (PMC9233046). Converter pela IQR do próprio estudo em vez de "3 ms por Kp". |
| 82 | incerteza do SDNN | `15.0` ms constante | **sem fonte** | Usar o erro-padrão implícito no IC de Ong (≈ 4.3 ms para o RMSSD) ou rotular. |
| 92, 98-103 | enxaqueca: `baseline_prob 0.05`, `dkp_sensitivity 0.02`, limiar `dkp > 2`, fator `* 10.0`, teto `0.5`, incerteza `× 0.3` | — | **sem fonte nenhuma** (6 constantes) | Remover o modelo ou rotular exploratório (grau D) com aviso explícito; o fator `* 10.0` não tem justificativa dimensional. |
| 110-114 | melatonina: `0.15` (Kp ≥ 7), `0.08` (Kp ≥ 5), incerteza `× 0.5` | — | **sem fonte**. O documento classifica a hipótese como "dados inconsistentes em humanos" (Burch et al. 1999, doi 10.1016/S0197-4580(99)00043-1) | Rotular grau D e citar Burch 1999 apenas como hipótese; remover os percentuais. |
| 119-126 | qualidade do sono (o limiar `dst < -50` da linha 123 também): `75`, `3.0`/Kp, `0.05`/nT, piso `30`, incerteza `10` | — | **sem fonte nenhuma** | Remover ou rotular exploratório. |
| 132-139 | dose de aviação: `3.0` µSv/h a 10 km, `exp(0.2·Δh)`, `1 + 0.5·sin(lat)` | — | **sem fonte** ("simplified CARI-7 approximation" sem citação). **Dois defeitos:** (a) `sin` é ímpar, então o fator cai ao sul do equador (lat < 0 → `lat_factor < 1`), mas a dose depende da magnitude da latitude geomagnética (rigidez de corte), simétrica entre hemisférios; (b) a série `x − x³/6` erra 0.5 % em 60° e 7.5 % em 90° (sin(π/2) = 1, série = 0.925) | Usar `abs(lat)` (melhor: latitude geomagnética), `sin` por FFI (`sin` consta entre as funções FFI suportadas, `docs/guide/LLM_PROGRAMMING_GUIDE.md` §13) e citar CARI-7/ICRP; senão rotular exploratório. |
| 145-149 | evento de partículas: `1 + 2·ln(f/10)`, incerteza `× 0.3` | — | O limiar de 10 pfu é o S1 da NOAA (**fonte: escala NOAA S**); o fator `2.0` e a incerteza **sem fonte** | Citar a escala S e rotular o ganho 2.0 exploratório. |
| 160 | Schumann: `f1 = 7.83 Hz`, `q_factor = 5.0` | — | 7.83 Hz é o valor de livro da fundamental; `5.0` **sem citação**. O documento chama a relação cérebro–Schumann de "especulativa" | Citar a fonte da fundamental; Q em faixa com referência. |
| 164-168 | desvio do Schumann: `-0.1·(Kp−4)` Hz, `1 + 0.2·(Kp−4)` | — | **sem fonte nenhuma** | Remover ou rotular grau D. |

Resumo: 14 linhas da tabela, das quais **nenhuma** traz referência no próprio arquivo; para `kp_coeff` (e a incerteza do RR), o efeito de HRV e o limiar de 10 pfu há uma fonte candidata (acima), as demais não encontrei.

## `constants.sio`
Contém apenas `//! Heliophysics constants (disabled — pending pub const and unit type support)`. O mesmo diretório já usa o padrão `fn NAME() -> f64 { … }` em `indices.sio` (`KP_QUIET()` etc.), que não depende de `pub const`. Sugestão: habilitar `constants.sio` nesse formato com as constantes calibradas e graduadas do darwin-heliobiology (Kp/9, |Dst|/78 nT, Bz sul/8.7 nT, pressão dinâmica 1.6726e-6·n·v²/7.30 nPa, std(Kp, ddof=1)/1.57; p99 sobre OMNI2 2020-2025, 52 608 horas, grau B) e fazer `effects.sio` importá-las, para existir uma única fonte.

## Por que abrir uma issue e não editar
O pedido era só auditar: o stdlib do Sounio é do mantenedor do compilador e a correção das fontes precisa de revisão humana dos artigos.
