# Fixtures SWPC

Gravações reais (curl, 2026-10-06) de `services.swpc.noaa.gov`, via `scripts/collect_raw.sh swpc`:

| arquivo | feed | observação |
|---|---|---|
| `kp_3h.json` | `/products/noaa-planetary-k-index.json` | Kp de 3 h, chave `Kp`, `time_tag` SEM fuso (= UTC) |
| `dst_kyoto_object.json` | `/products/kyoto-dst.json` | Dst Kyoto, lista de objetos `{time_tag, dst}` |
| `dst_kyoto_legacy_table.json` | derivado de `dst_kyoto_object.json` | forma legada (tabela: 1ª linha cabeçalho, valores como string). Derivado por `jq`, não gravado |
| `rtsw_mag_1m.json` | `/json/rtsw/rtsw_mag_1m.json` | 300 primeiros registros (mais novos primeiro); `active` true/false |
| `rtsw_wind_1m.json` | `/json/rtsw/rtsw_wind_1m.json` | idem; `proton_speed`/`proton_density` podem ser `null` |

`edge_cases.json` é escrito à mão (casos de borda do parser). O feed completo fica em `data/raw/swpc/` (não versionado).
