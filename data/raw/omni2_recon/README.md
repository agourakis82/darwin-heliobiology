# OMNI2 2020-2025 reconstruído (não é o arquivo cru da NASA)

`omni2_2020-2025.dat.xz` = os 6 arquivos anuais `omni2_YYYY.dat` concatenados (52 608 linhas, uma por
hora), no layout de texto OMNI2 (55 colunas, Kp ×10, fills 999.9 / 9999. / 99.99 / 99 / 99999).

**Proveniência honesta.** `spdf.gsfc.nasa.gov` não é alcançável da máquina de desenvolvimento
(timeout de conexão IPv4 e IPv6, tanto no t560 quanto no Mac; medido em 2026-10-06 com
`curl --connect-timeout 8`), então o arquivo cru não pôde ser baixado aqui. Estes arquivos foram
re-serializados por `scripts/reconstruct_omni2_dat.py` a partir de `data/raw/nasa_omni/omni2_hourly.parquet`
(a mesma série que o Python já usava; o round-trip pelo parser Python corrigido reproduz o parquet
bit a bit, 9/9 colunas). As colunas que o parser não usa saem com fill. Só conversão de formato;
nenhum valor é calculado.

Onde a rede alcançar a NASA, `scripts/collect_raw.sh omni2` baixa os arquivos reais em
`data/raw/omni2/` e o gate usa esses no lugar (variável `OMNI_DAT`).

Descompactar: `make omni-dat` (gera `build/data/omni2_2020-2025.dat`).
