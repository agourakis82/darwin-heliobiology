# Fixture OMNI2

`sample.dat` e escrito a mao no layout OMNI2 (55 colunas; so as colunas usadas pelo parser tem valor):

| linha | caso |
|---|---|
| 1 | valores normais; Kp*10 = 27 |
| 2 | Kp*10 = 30, Bz positivo |
| 3 | TODAS as colunas usadas em fill (999.9 / 9999. / 99.99 / 99 / 99999) |
| 4 | Kp*10 = 0 (Kp real 0.0 e DADO), Dst = -78, Bz = -8.8 |
| 5 | 2024 dia 366 hora 23 (ano bissexto), Kp*10 = 90 |
| 6 | linha curta (3 tokens) -> `bad_lines` |
| 7 | linha em branco -> ignorada |
| 8 | 2020 dia 60 (29-fev-2020) |

`atlas.dat` (8 registros, 2024): fev-28 (3 h), fev-29 (2 h), mar-01 (1 h), abr-01 (tudo em fill),
jul-15 (1 h). Kp*10 = 50 / 49 / 99(fill) / 67 / 20 / 10 / 99(fill) / 90 — o 50 (Kp 5.0 exato) fica
NO limite de tempestade (Kp >= 5), o 49 (4.9) fica fora. Valores esperados em `sio/test_atlas.sio`.
