## Resumo
`metrics/helio_index.py::_latest_timestamp` toma o `timestamp` do **último elemento** de cada série, não o máximo. Com séries em ordem decrescente — como o feed RTSW do SWPC (`rtsw_mag_1m.json`, `rtsw_wind_1m.json`: o primeiro registro é o mais novo) — o instante de referência da janela de 12 h sai errado (pega a amostra mais *antiga*) e a janela inclui dados que deveriam estar fora, ou exclui dados novos.

Achado pela corroboração Python × núcleo Sounio (`make corroborate`). Os dois caminhos Sounio (principal e gêmeo) **e** a referência F# (escritos a partir de `docs/SIO_CORE_SPEC.md` §4: `t_end` = maior `t` entre todas as amostras) concordam entre si; só o Python diverge, então a correção é no Python (ADR-008/009: o Sounio não é ajustado para casar com Python).

## Reprodução
`tests/fixtures/helio/window.txt` (na branch `feat/sounio-core`):

```
KP 100000 1.0
KP 96400 3.0
KP 56800 9.0      # exatamente em t_end-43200 se t_end = 100000: FORA da janela
KP 50000 9.0
DST 99000 -40
DST 60000 -78
DST 50000 -200
BZ 100000 5.0
BZ 99000 -9.0
WIND 100000 5.0 400.0
WIND 99000 NA 450.0
```

| grandeza | Sounio (principal = gêmeo = F#) | Python |
|---|---|---|
| `comp kp` | 0.2222 (média de {1, 3} / 9) | 0.4815 (média de {1, 3, 9} / 9) |
| `comp variability` | 0.9008 | 1 (saturado) |
| `score` | 0.5038 | 0.5995 |

Python calcula `t_end = 99000` (último elemento de `imf`/`solar_wind`) e inclui a amostra de t=56800.

## Correção sugerida
`max(...)` sobre **todos** os timestamps de todas as séries (inclusive amostras de valor ausente), como a spec; ou ordenar cada série antes.

## Notas
- Comentário em `_build_alerts`: `# Kp ≥ 6.3 ≈ G3 (NOAA)` — na escala NOAA G3 é Kp 7 (Kp 6 = G2); 6.3 é só o limiar 0.7·9.
