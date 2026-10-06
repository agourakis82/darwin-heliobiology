# Núcleo de cálculo em Sounio, validado pelo ADR-009 (+ ADR-008)

Branch `feat/sounio-core` → `main`. **Sem merge.** Reescreve em Sounio (`sio/`) o núcleo de cálculo; oráculos em `oracles/` (F#, Futhark, F\*); gate `make sio-test`; job de CI separado; corroboração Python só como relatório. Especificação única de onde todas as implementações saem: `docs/SIO_CORE_SPEC.md` (as referências estrangeiras foram escritas **só** a partir dela, ADR-009 §1 critério 1).

Regra de ouro cumprida: nada está "pronto" sem `souc check`, `souc run` e o gate de oráculo verde — saídas coladas abaixo. Toolchains fixados em `gate/toolchains.env`: `souc` = **Madaros v0.80.0** (Sounio-lang/sounio `4871d3fa0`), .NET SDK 9.0.300, Futhark 0.27.1, F\* 2026.09.27.

## ⚠️ O que mudou em relação ao pedido (leia primeiro)

1. **O patch `fix/data-integrity` não chegou** (não estava no repositório, nem em branch/PR, nem anexado ao texto que recebi). Foi **reconstruído** por auditoria do Python contra a spec (commit `1aa4327`, 117 testes verdes); não é o patch original. O que ele corrige está no `CHANGELOG.md` (Kp ÷ 10 na leitura, janela de 12 h por tempo, ddof=1, "ausente nunca vira 0", `storm_hours`, Fisher-z com |r| = 1…). Se o patch original existir, rebaseie/compare: a corroboração Python depende dele.
2. **`spdf.gsfc.nasa.gov` é inalcançável** daqui (timeout IPv4 e IPv6, no t560 e no Mac; `curl --connect-timeout 8`). O OMNI2 usado no gate é a **mesma série** (52 608 h, 2020-2025) **re-serializada no layout `.dat`** a partir do parquet versionado (`scripts/reconstruct_omni2_dat.py`, só conversão de formato; round-trip pelo parser Python corrigido reproduz o parquet 9/9 colunas bit a bit). Está em `data/raw/omni2_recon/` (xz, 608 KB, com SHA256) e o README lá diz isso. Onde houver rota, `scripts/collect_raw.sh omni2` baixa o cru e `OMNI_DAT=…` o usa no gate. **Os feeds SWPC são reais** (gravados 2026-10-06).
3. **O CI novo não foi executado num runner do GitHub** (só localmente: `make sio-test` verde de um `build/` limpo, 2 min). O workflow é `.github/workflows/sio-core.yml`, independente do `ci.yml` (que continua, sem veto sobre o núcleo). O job Python antigo já estava vermelho em `main` neste ambiente (ruff 313 achados, mypy 3); esta branch deixa ruff em 315.

## Tabela módulo × gate

`check` = `souc check` limpo (sem warning/error); `run` = `souc run` com a linha sentinela; gêmeo = principal × `sio/twin/` com algoritmo diferente; referência = `verified_foreign_reference` (ADR-009). "máx. medido" é a maior diferença relativa observada entre as implementações.

| módulo | check | run (sentinela) | gêmeo (algoritmo diferente) | referência ADR-009 | tolerância (declarada → máx. medido) |
|---|---|---|---|---|---|
| a `omni.sio` | ✅ | `OMNI_FIXTURE_OK` | — (parser de formato) | contagens/quantis sobre 52 608 h conferidos pelo parser F# independente (bloco `calib`) | contagens exatas; valores via `calib`: 1e-9 → 1.9e-16 |
| b `swpc.sio` | ✅ | `SWPC_FIXTURES_OK` | — | esperados independentes via `jq` (soma/contagem) nos testes | 1e-9 nos testes unitários |
| c `helio_index.sio` | ✅ | `HELIO_CASES_OK` | janela por idade, Dst por `max(-x,0)`, Kahan, std em duas passadas × Welford, produto interno | **F#** (`HelioOracle helio`) + **F\*** (4 invariantes) | 1e-12 → 1.5e-16 (F#), 1.5e-16 (gêmeo) |
| d `atlas.sio` | ✅ | `ATLAS_CASES_OK` | endereçamento direto por índice de período + Kahan × varredura com mudança de chave | F\*: `storm_hours ≤ valid_hours` | 1e-12 (diário, `floor 1e-2`: médias de Bz que se cancelam), 1e-9 mensal/trimestral → 6.4e-14 |
| e `calibration.sio` | ✅ | `CALIB_CASES_OK` | quickselect (Hoare, mediana de 3) × heapsort; dois ponteiros × varredura p/ trás | **F#** (p99 + parser próprio) | 1e-9 → 9.7e-15 (gêmeo), 1.9e-16 (F#) |
| f `passport.sio` | ✅ | `PASSPORT_CASES_OK` | produto de z-scores × somas centradas; SplitMix64 reescrito | **Futhark** (fluxo SplitMix64 exato **e** distribuição nula com outro PRNG) | 1e-9 → 7e-15 (gêmeo), 0 (Futhark: T_obs, p, os 1000 T_b) |
| g `meta.sio` | ✅ | `META_CASES_OK` | forma matricial (`P = W − W11ᵀW/s`, `Q = yᵀPy`, `C = trP`, GLS por Gauss–Jordan) × momentos | **F#** | 1e-12 → 1.7e-15 (gêmeo), 0 (F#) |

Toda tolerância > 1e-12 tem a causa escrita em `gate/tolerances.tsv`. O comparador é o do oráculo F# (`HelioOracle compare`); Python não participa de nenhum veredito.

### Saídas coladas (`make sio-test`, build limpo, rc=0, 2 min 06 s)

```
souc check: 29/29 arquivos limpos
ok   run sio/test_atlas.sio  ATLAS_CASES_OK
ok   run sio/test_calib.sio  CALIB_CASES_OK
ok   run sio/test_helio.sio  HELIO_CASES_OK
ok   run sio/test_meta.sio  META_CASES_OK
ok   run sio/test_num.sio  NUM_OK
ok   run sio/test_omni.sio  OMNI_FIXTURE_OK
ok   run sio/test_passport.sio  PASSPORT_CASES_OK
ok   run sio/test_swpc.sio  SWPC_FIXTURES_OK
testes .sio: 8/8 verdes
blocos: principal=19 gemeo=19          (3 694 linhas comparadas)   AGREE   TWIN_GATE_OK
F#: 11 blocos (172 linhas)  AGREE   |  Futhark passport n=2400, B=1000 (1 008 linhas)  AGREE
p=0.5  F=0.48575 B1=1000 B2=20000 z=4 |F-p|=0.01425  bound=0.0648  IN_BAND
p=0.9  F=0.8958  ...                  |F-p|=0.0042   bound=0.0389  IN_BAND
p=0.95 F=0.9376  ...                  |F-p|=0.0124   bound=0.0282  IN_BAND
p=0.99 F=0.98365 ...                  |F-p|=0.00635  bound=0.0129  IN_BAND
FOREIGN_GATE_OK
FSTAR_GATE_OK       inventario: 24 linhas, 0 problemas   INVENTORY_OK
SIO_TEST_OK
```

**Os gates falham quando devem (mutações aplicadas e revertidas):** (1) constante `78 → 79` no núcleo ⇒ gêmeo **e** F# divergem (`comp dst` 1.3e-2); (2) quantil do gêmeo com `h = q·N` ⇒ gêmeo diverge do núcleo; (3) `bounded` do PRNG do núcleo com `>> 12` ⇒ o **gêmeo não vê** (usa o mesmo PRNG, daí o Futhark) e o Futhark reprova o fluxo compartilhado. Validador do inventário: Python como `verified_foreign_reference` é rejeitado.

## Provas F\* (`oracles/fstar/Helio.Props.fst`, F\* 2026.09.27, sem `admit`/`assume`)

`All verification conditions discharged successfully`, teoremas: `clip01_in_unit_interval`, `component_in_unit_interval_{kp,dst,bz,pressure,variability}`, `weights_sum_to_one`, `weights_nonneg`, `score_in_unit_interval`, `score_monotone_{kp,dst,bz,pressure,variability}`, `ensure_kp_scale_in_range`, `ensure_kp_scale_idempotent`, `storm_hours_le_valid_hours`, `valid_hours_le_length`. **Controle negativo** (`check.sh --negative`): F\* rejeita as 5 variantes falsas (clip sem limite inferior, peso negativo, pesos somando 1.05, `ensure_kp_scale` que só reescala acima de 90, `storm` contado sobre mais leituras que `valid`). Modelo sobre ℝ (`FStar.Real`); o arredondamento é abstraído porque clip, soma e produto por constantes ≥ 0 são monotônicos sob arredondamento ao mais próximo.

## Corroboração Python (só relatório — `make corroborate`, nunca falha)

144 comparações (helio × 5 casos, calib × 2 arquivos, atlas diário/mensal/trimestral × 2, meta × 4, passaporte × 2), **141 concordam**. Divergências:

| caso | grandeza | Sounio (= gêmeo = F#) | Python | rel |
|---|---|---|---|---|
| helio `window.txt` | comp kp | 0.2222 | 0.4815 | 5.4e-1 |
| helio `window.txt` | comp variability | 0.9008 | 1 | 9.9e-2 |
| helio `window.txt` | score | 0.5038 | 0.5995 | 1.6e-1 |

Causa: `_latest_timestamp` usa o **último elemento** das séries, não o máximo (o feed RTSW vem do mais novo para o mais antigo). Confirmada por gêmeo + F# como acerto do Sounio ⇒ **issue no darwin-heliobiology** (agourakis82/darwin-heliobiology#3), sem ajuste no Sounio.

## Tempos no OMNI2 completo (52 608 h, 20 MB; mediana de 3; tempo de parede com partida do processo)

| tarefa | Sounio principal | Sounio gêmeo | F# (.NET 9.0.300) | Futhark 0.27.1 (`c`, sequencial) |
|---|---|---|---|---|
| parse OMNI2 + resumo | 0.51 s | — | — | — |
| calibração p99 (5 séries + kp_var) | 0.60 s | 0.56 s | 0.62 s | — |
| atlas mensal | 0.51 s | 0.53 s | — | — |
| passaporte n=52 608, lags 0..72, B=100 | 19.43 s | 35.17 s | — | 2.00 s |

Madaros aguenta 52 608 × 8 colunas f64 no heap (3.4 MB) sem problema; medido além: `read_file` de 400 MB, `heap_alloc` de 1 GiB e `struct { a: [f64; 52608] }` — nenhum limite encontrado.

## Limites da linguagem encontrados (nenhum contornado em silêncio)

| limite | efeito | o que fiz | issue |
|---|---|---|---|
| `u64`: `>>` sobre **parâmetro** é aritmético; `>` é com sinal (Madaros e lean_single) | SplitMix64 em `u64` sai errado (e deu SIGSEGV no primeiro passaporte que escrevi) | SplitMix64 em `i64` + deslocamento lógico explícito, conferido contra os vetores públicos | #2830 (cita #2084) |
| `measure()` dentro de laço ⇒ variância 0 em silêncio; variância de 1ª ordem não atravessa chamadas (KL-11) | GUM do DL | `dl_pooled_gum` numa **única** função, corpo desenrolado, **≤ 12 estudos**; resultado como par (valor, variância), não `Knowledge` atravessando a chamada; var = 1/Σw\* = se² verificado no teste | #2827 |
| struct de usuário chamado `Box` sombreia o builtin; `check` verde, ELF dá SIGSEGV | custou uma bissecção | nome evitado | #2828 |
| Madaros não exige `IO`/`Mut` (o `lean_single` exige) | código "limpo" no `check` que só roda num motor | todos os efeitos declarados (29 arquivos) | #2834 |
| `stdlib/json` e `csv`: 4096 B / 256 linhas | não servem ao OMNI2 (20 MB) nem ao RTSW (1.7–2.9 MB) | `read_file` + parsers próprios (subconjunto JSON declarado em `swpc.sio`) | — |
| KL-11 | variância de 1ª ordem não cruza funções | declarado, ver acima | — |

## Divergências Madaros × lean_single (§4)

`make lean-single`: 7 de 8 testes passam também sob `lean_single`; os 19 blocos do driver principal e do gêmeo coincidem com o Madaros num recorte < 16 MiB do OMNI. Divergências (cada uma com programa mínimo em `docs/divergences/` e issue em Sounio-lang/sounio):

| # | divergência | issue |
|---|---|---|
| D01 | xorshift64\* em `u64`: Madaros 1934872821 (correto), lean_single −212610827 | [#2825](https://github.com/Sounio-lang/sounio/issues/2825) |
| D02 | literal `1.0e-300` arredondado 13 ulps fora no lean_single | [#2826](https://github.com/Sounio-lang/sounio/issues/2826) |
| D03 | variância GUM dentro de uma função: Madaros ✓ / lean_single 0; atravessando chamada: o inverso (explica a falha de `test_meta` sob lean_single) | [#2827](https://github.com/Sounio-lang/sounio/issues/2827) |
| D04 | `struct Box`: Madaros SIGSEGV / lean_single ✓ | [#2828](https://github.com/Sounio-lang/sounio/issues/2828) |
| D05 | `print_int(floor(7.9) as i64)`: lean_single para em silêncio | [#2829](https://github.com/Sounio-lang/sounio/issues/2829) |
| D06/07 | `u64` `>>` em parâmetro e `>` com sinal (ambos os motores) | [#2830](https://github.com/Sounio-lang/sounio/issues/2830) |
| D08 | `use` resolvido relativo ao CWD no lean_single | [#2831](https://github.com/Sounio-lang/sounio/issues/2831) |
| D09 | **`read_file` trunca em silêncio em 16 MiB no lean_single** (o OMNI inteiro lê 43 919 de 52 608 linhas) | [#2832](https://github.com/Sounio-lang/sounio/issues/2832) |
| D10 | `var` aceito como nome de campo só no Madaros | [#2833](https://github.com/Sounio-lang/sounio/issues/2833) |
| D11 | efeitos `IO`/`Mut` não impostos no Madaros | [#2834](https://github.com/Sounio-lang/sounio/issues/2834) |

## Auditoria `stdlib/heliobiology` (§5) — só issue, stdlib não editado

[Sounio-lang/sounio#2835](https://github.com/Sounio-lang/sounio/issues/2835): cada constante sem referência de `effects.sio` (kp_coeff 0.03, dst_coeff 0.01, incerteza fixa de 15 %, enxaqueca, melatonina, sono, dose de aviação — com um defeito de sinal em `sin(lat)` e série de Taylor com erro de 7.5 % em 90° —, Schumann), com a correção sugerida onde há fonte candidata (Vencloviene 2022, Ong 2022) e a proposta de habilitar `constants.sio` (desabilitado) no padrão `fn NAME() -> f64`.

## Fora de escopo (e por quê)

Streamlit (dashboard, UI), TFT/PatchTST (previsão neural; sem equivalente em Sounio, depende de torch), PCMCI+ (descoberta causal; tigramite), ingestão WESAD (dataset externo, sem dados aqui). O alinhamento HRV × solar do passaporte também fica de fora: `passport.sio` recebe séries já alinhadas. **Koka e C++23 não são usados** (o ADR reserva Koka para semântica de efeitos e C++23 para integridade de bootstrap).

## Reprodução

```bash
make toolchains && make sio-test        # gate completo (Python não participa)
make corroborate                        # relatório Python (só informativo)
make bench && make lean-single          # tempos e divergências Madaros x lean_single
```
`oracles/claim_oracle_inventory.tsv` (24 linhas, formato do schema do Sounio, validado por `gate/inventory_check.sh`) tem uma linha por claim: módulo, propriedade, `oracle_class`, toolchain fixado e motivo.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
