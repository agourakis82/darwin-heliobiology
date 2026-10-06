# Especificação do núcleo de cálculo (Sounio)

Esta especificação é a **única fonte** a partir da qual as implementações do núcleo são
escritas: o núcleo Sounio (`sio/`), os gêmeos (`sio/twin/`) e as referências estrangeiras
verificadas (`oracles/`, ADR-009 §1 critério 1: *escritas a partir da especificação, nunca
transliteradas do Sounio*). Quem implementa um oráculo lê SÓ este documento.

Versão da spec: **1**. Constantes e pesos vêm de `docs/SCIENTIFIC_FOUNDATIONS.md` §5.

## 0. Convenções

* **Tempo**: inteiro, segundos desde 1970-01-01T00:00:00Z (`t`). `time_tag` sem fuso é UTC.
* **Ausente** é um estado explícito (`NA`), nunca um número. Ausente **nunca** vira 0.
  Valores ausentes saem das contagens e das somas; um agregado sem nenhuma amostra válida é
  ele próprio ausente.
* Aritmética em IEEE-754 binary64. Nenhuma biblioteca estatística: só `+ − × ÷`, `sqrt`,
  `floor`, comparações.
* `mean(xs)`: soma sequencial na ordem dada ÷ contagem. `std1(xs)` (desvio-padrão amostral,
  ddof=1): `sqrt(Σ(x−mean)² / (n−1))`, definido só para n ≥ 2. `std0` usa `n`.
* `clip01(x) = min(1, max(0, x))`.

### 0.1 Token numérico exato (saída dos programas)

Todo f64 impresso por um programa do gate usa um token que não perde bits:

| valor | token |
|---|---|
| ausente | `NA` |
| zero (±0) | `0` |
| NaN | `nan` |
| ±∞ | `+inf` / `-inf` |
| finito normal `x = ±1.f × 2^e` | `<s><n>p<e>`: `s` é `+`/`-`, `n` o inteiro `1.f × 2^52` (∈ [2^52, 2^53), decimal), `e` o expoente com sinal explícito (`+`/`-`) |

Exemplo: `1.0 → +4503599627370496p+0`; `-0.5 → -4503599627370496p-1`; `3.0 → +6755399441055744p+1`.
Subnormais não ocorrem nas entradas; um programa pode abortar com erro se encontrar um.
Inteiros saem em decimal. Rótulos são ASCII sem espaço.

### 0.2 Comparação entre implementações

Dois tokens numéricos `a`, `b` concordam com tolerância relativa `tol` se
`|a−b| ≤ tol · max(|a|, |b|, 1e-6)`. `NA` só concorda com `NA`. `tol` default `1e-12`;
quantis e somas longas (≥ 1000 termos) usam `1e-9`. Tolerância maior só com a causa escrita
em `gate/tolerances.tsv`. O comparador é `oracles/fsharp` (`compare`).

## 1. Protocolo dos programas do gate

Todo programa do gate (Sounio principal, gêmeo, F#, Futhark) lê o arquivo de comandos
`build/gate/cmd.txt` (um comando por linha, tokens separados por espaço, `#` inicia comentário)
e imprime em stdout, para cada comando, um bloco que começa com `begin <comando> <args…>` e
termina com `end`. Linhas dentro do bloco são `<rótulo> <token…>`. Caminhos são relativos à
raiz do repositório.

## 2. OMNI2 (`omni`)

Arquivo texto, uma linha por hora, colunas separadas por espaços, **≥ 41** colunas
(índices 0-based). Linhas em branco são ignoradas; linha com < 41 colunas conta em `bad_lines`.

| col | variável | fill (ausente se valor ≥ fill) |
|---|---|---|
| 0, 1, 2 | ano, dia do ano (1-based), hora (0–23) | — |
| 12 | Bx GSE (nT) | 999.9 |
| 15 | By GSM (nT) | 999.9 |
| 16 | Bz GSM (nT) | 999.9 |
| 23 | densidade de prótons n (cm⁻³) | 999.9 |
| 24 | velocidade v (km/s) | 9999 |
| 28 | pressão de fluxo (nPa) | 99.99 |
| 38 | Kp × 10 | 99 |
| 40 | Dst (nT) | 99999 |

`t = ((dias desde 1970-01-01 de (ano, 1, 1)) + doy − 1)·86400 + hora·3600`.
**Kp = coluna 38 ÷ 10 na leitura.** Os valores válidos entram como lidos (Kp ÷ 10 exato por
divisão correta). Registros ficam na ordem do arquivo, sem deduplicar.

`omni <arquivo>…` imprime: `n_records`, `bad_lines`, `t_first`, `t_last`, e para cada
variável `bx by bz n v p kp dst`: `count <var> <int>` (válidos), `sum <var> <tok>` (soma
sequencial dos válidos), `min`, `max`, `wsum <var> <tok>` (Σ x_i·(i mod 7 + 1), i = índice
do registro no conjunto concatenado, só válidos).

## 3. SWPC (`swpc`)

JSON, subconjunto: lista plana de objetos (valores número, string, bool, null) — ou, na forma
legada do Dst, lista de listas (tabela). Feeds:

1. **Kp 3 h** (`kp_3h.json`): objetos `{"time_tag", "Kp", …}`. Registro `(t, Kp)`; `Kp` nulo → ausente.
2. **Dst Kyoto, objeto** (`dst_kyoto_object.json`): `{"time_tag", "dst"}`.
3. **Dst Kyoto, tabela legada** (`dst_kyoto_legacy_table.json`): primeira linha é cabeçalho
   (lista cuja 1ª célula é a string `time_tag`) e é descartada; demais linhas `[time_tag, valor]`,
   valor string numérica ou número; `null` → ausente.
4. **RTSW mag** (`rtsw_mag_1m.json`): só objetos com `"active": true`; campos `bx_gsm`, `by_gsm`, `bz_gsm`.
5. **RTSW vento** (`rtsw_wind_1m.json`): só `"active": true`; `proton_speed`, `proton_density`.

Em qualquer campo numérico, `null` ou o valor exato `-9999` → ausente. `time_tag` =
`YYYY-MM-DDTHH:MM:SS` seguido opcionalmente de fração `.fff…` (ignorada), e de um sufixo de fuso:
nenhum ou `Z` (UTC), `+HH:MM`, `-HH:MM` (aplicar o deslocamento). Ordem dos registros: a do arquivo.

`swpc <kp|dst_obj|dst_tab|mag|wind> <arquivo>` imprime `n_records`, `t_first`, `t_last`
(do 1º e do último registro **do arquivo**, não min/max) e, por campo, `count`, `absent`, `sum`, `min`, `max`.

## 4. HelioMind Index (`helio`)

Entrada (arquivo de caso, uma linha por amostra):

```
NOW  <t>                 # instante usado se não houver nenhuma amostra
KP   <t> <valor|NA>      # Kp na escala real 0–9
DST  <t> <valor|NA>      # nT
BZ   <t> <valor|NA>      # Bz GSM, nT
WIND <t> <n|NA> <v|NA>   # densidade cm⁻³, velocidade km/s
```

Seja `t_end` o maior `t` entre **todas** as linhas de amostra (inclusive as de valor ausente);
sem amostras, `t_end = NOW`. A janela é `W = { amostra : t_end − 12·3600 < t ≤ t_end }` (por tempo).
Dentro de `W`, só amostras válidas contam:

| componente | definição (sobre as amostras válidas de `W`) | ausente se |
|---|---|---|
| `kp` | `clip01(mean(Kp)/9)` | não há Kp válido |
| `dst` | `clip01(|min(min(Dst), 0)| / 78)` | não há Dst válido |
| `bz` | `clip01(mean(max(−Bz, 0)) / 8.7)` | não há Bz válido |
| `pressure` | `clip01(mean(1.6726e-6·n·v²) / 7.30)`, amostra `WIND` só vale se `n` e `v` válidos | nenhuma amostra de vento completa |
| `variability` | `clip01(std1(Kp) / 1.57)` | menos de 2 Kp válidos |

`score = clip01(0.35·kp + 0.25·dst + 0.20·bz + 0.15·pressure + 0.05·variability)`, **estrito**:
se qualquer componente é ausente, `score` é ausente e `class = 3` (`indisponivel`).
Senão `class = 0` (`estavel`) se `score < 0.33`, `1` (`vigilancia`) se `score < 0.66`, senão `2` (`alerta`).
`alerts` é uma máscara de bits (bit 0 = 1: `kp ≥ 0.7`; bit 1 = 2: `dst ≥ 0.6`; bit 2 = 4: `bz ≥ 0.5`;
bit 3 = 8: `pressure ≥ 0.5`; bit 4 = 16: `variability ≥ 0.6`); componente ausente não alerta.

Saída por caso: `t_end`, `n_window kp dst bz wind` (4 inteiros: amostras válidas em `W`),
`comp kp|dst|bz|pressure|variability <tok>`, `score <tok>`, `class <int>`, `alerts <int>`.

Comando: `helio <arquivo-de-caso>`.

## 5. Atlas (`atlas`)

Entrada: os mesmos arquivos OMNI da §2 (concatenados). Resolução `daily`, `monthly` ou
`quarterly`. Período de um registro: dia `YYYY-MM-DD`, mês `YYYY-MM`, trimestre `YYYY-Qq`
(UTC, a partir de `t`). Períodos em ordem cronológica; só períodos com ≥ 1 registro (mesmo que
todos os valores sejam ausentes). Por período (somente amostras válidas):

* `mean_kp`, `mean_dst`, `mean_bz`: `mean`, ausente se nenhuma amostra válida;
* `storm_hours`: número de Kp válidos com `Kp ≥ 5.0`; `valid_hours`: número de Kp válidos;
  sempre `storm_hours ≤ valid_hours`;
* `min_dst`: mínimo (ausente se nenhum Dst válido);
* `bz_south_frac`: (nº de Bz válidos `< 0`) ÷ (nº de Bz válidos), ausente se nenhum.

Comando `atlas <daily|monthly|quarterly> <arquivo>…`; saída: `n_periods <int>` e, por período,
`period <rótulo> <mean_kp> <mean_dst> <mean_bz> <storm_hours> <valid_hours> <min_dst> <bz_south_frac>`.

## 6. Calibração (`calib`)

Entrada: arquivos OMNI (§2). Cinco séries por registro:

| série | definição | ausente se |
|---|---|---|
| `kp` | Kp | Kp ausente |
| `dst_abs` | `|min(Dst, 0)|` | Dst ausente |
| `bz_south` | `max(−Bz, 0)` | Bz ausente |
| `pressure` | `1.6726e-6·n·v²` (nPa) | `n` ou `v` ausente |
| `kp_var` | `std1` dos Kp **válidos** com `t_j ∈ (t_i − 12·3600, t_i]` | menos de 2 Kp válidos na janela |

Para cada série, sobre os valores presentes: `count`, `mean`, e os quantis `p50 p90 p95 p99`
por interpolação linear entre ordens: ordene crescente (`x_0 ≤ … ≤ x_{N−1}`), `h = q·(N−1)`,
`lo = floor(h)`, `Q(q) = x_lo + (h − lo)·(x_{lo+1} − x_lo)` (se `lo = N−1`, `Q = x_lo`).

Divisores sugeridos: `kp` é fixo em `9.0`; os demais `max(p99, 1.0)`. Alvos publicados
(`docs/SCIENTIFIC_FOUNDATIONS.md` §5.2): `9.0 / 78 / 8.7 / 7.30 / 1.57`. `target_ok <série>`
é `1` se `|suggested − alvo| ≤ 0.005`, senão `0`.

Comando `calib <arquivo>…`; saída: `n_records`, e por série (`kp dst_abs bz_south pressure kp_var`):
`count`, `mean`, `p50`, `p90`, `p95`, `p99`, `suggested`, `target_ok`.

## 7. Passaporte: correlação cruzada e teste de permutação (`passport`)

Entradas: `x[0..n−1]`, `y[0..n−1]` (sem ausentes), `lag_max`, `B`, `seed` (u64).

`r(ℓ)` para `ℓ ∈ 0..lag_max` com `m = n − ℓ ≥ 10`: Pearson entre `x[0..m−1]` e `y[ℓ..n−1]`
(`x` à frente de `y` em `ℓ`). Se `std0` de qualquer um dos dois segmentos `< 1e-12`, o lag é ignorado.
`T = max_ℓ |r(ℓ)|` (0 se nenhum lag válido) e `lag*` o `ℓ` (o menor, em empate) que o atinge.

**Permutação por blocos de 24 h** da série `y`: blocos consecutivos de 24 índices (o último pode
ser menor), `K = ceil(n/24)`. A ordem dos blocos é embaralhada por Fisher–Yates
(`i = K−1 … 1`: `j = bounded(i+1)`; trocar `ordem[i]` e `ordem[j]`, `ordem` iniciando na identidade)
e `y'` é a concatenação dos blocos na nova ordem. Para a permutação `b = 0 … B−1`:

* PRNG **SplitMix64**: `state += 0x9E3779B97F4A7C15; z = state; z = (z ^ (z>>30)) * 0xBF58476D1CE4E5B9;
  z = (z ^ (z>>27)) * 0x94D049BB133111EB; saída = z ^ (z>>31)`, aritmética módulo 2⁶⁴ (sem sinal);
* estado inicial da permutação `b`: `seed XOR ((b+1) * 0x9E3779B97F4A7C15 mod 2⁶⁴)`;
* `bounded(m) = (saída >> 11) mod m`.

`T_b` é o `T` de `(x, y')`. `p = (1 + #{b : T_b ≥ T − 1e-12}) / (B + 1)`.

Comando `passport <caso>` com arquivo de caso:

```
LAGMAX <int>
B <int>
SEED <u64 decimal>
N <n>
X <n valores decimais, um ou mais por linha>
Y <n valores decimais>
```

(As linhas `X`/`Y` podem continuar em linhas seguintes que começam com `+`.) Saída:
`n`, `T_obs <tok>`, `lag_obs <int>`, `p <tok>`, `null <b> <tok>` (um por permutação, ordem de `b`),
`null_q50|q90|q95|q99 <tok>` (quantis do conjunto `{T_b}` pela regra da §6).

## 8. Meta-análise DerSimonian–Laird (`meta`)

Entrada: arquivo com linhas `STUDY <id> <y> <v>` (efeito e variância, `v > 0`), `k ≥ 1`.

```
w_i  = 1/v_i
yFE  = Σ w y / Σ w
Q    = Σ w (y − yFE)²
C    = Σ w − Σ w² / Σ w
tau2 = C > 0 ? max(0, (Q − (k−1)) / C) : 0
I2   = Q > 0 ? max(0, (Q − (k−1)) / Q) · 100 : 0
w*_i = 1/(v_i + tau2)
yRE  = Σ w* y / Σ w*
se   = sqrt(1 / Σ w*)
z    = yRE / se
ci   = yRE ± 1.959963984540054 · se
```

Comando `meta <arquivo>`; saída: `k`, `Q`, `tau2`, `I2`, `pooled_fe`, `pooled_re`, `se`, `z`,
`ci_lo`, `ci_hi`, e `gum_var <tok>` (só o núcleo Sounio principal: variância de `yRE` obtida por
propagação GUM, que deve coincidir com `se²`).

## 9. Propriedades para toda entrada (provadas em F*)

Sobre ℝ (a prova abstrai o arredondamento: `clip01`, soma e produto por constantes ≥ 0 são
monótonos sob arredondamento para o mais próximo, logo as propriedades valem para f64):

1. cada componente normalizado (`clip01(a/d)` com `d > 0`, `clip01(|min(a,0)|/d)`, `clip01(mean/d)`, …) está em `[0, 1]`;
2. o `score` é monotônico **não decrescente** em cada componente em `[0,1]` (pesos ≥ 0 somando 1);
3. `ensure_kp_scale(série)`: seja `m` o máximo da série (série vazia fica como está);
   se `m > 9.0` (a série só pode estar em escala ×10, pois Kp real ≤ 9) cada valor é dividido por 10; senão a série fica como está. Para toda série
   cujos valores estão em `[0, 90]`: todo valor da saída está em `[0, 9]` e
   `ensure_kp_scale(ensure_kp_scale(s)) = ensure_kp_scale(s)`;
4. `storm_hours ≤ valid_hours` no período (§5), para toda lista de leituras `Kp` com ausentes.
