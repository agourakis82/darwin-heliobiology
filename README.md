# DARWIN Heliobiology

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18558930.svg)](https://doi.org/10.5281/zenodo.18558930)

Computational platform for heliobiological studies applied to mental health — NOAA/NASA data ingestion, psychodynamic modeling, and Q1 scientific validation.

## Structure
- `src/darwin_heliobiology/` — phenomenological core (SolarAtlas, SolarPsychodynamics, Kairos/Aletheia services).
- `analysis/`, `dashboards/`, `clinical/`, `simulations/`, `manuscripts/` — sprint deliverables.
- `docs/` — roadmap, dataset catalog, data lake, ethics.

See full manifesto in `README.exocortex`.

## Development
```bash
poetry install
poetry run pytest
poetry run black src
poetry run ruff src tests
poetry run mypy src
```

## Roadmap
See `docs/ROADMAP.md` for sprints and deliverables.

## SOTA References

- Updated overview in `docs/SOTA_HELIOBIOLOGY.md` (recommended models, datasets, and experiments).

## Citation

To cite this software, use:

```bibtex
@software{agourakis2025darwin,
  title={DARWIN Heliobiology: v0.2.0 — Scientific Grounding},
  author={Agourakis, Demetrios Chiuratto},
  year={2025},
  doi={10.5281/zenodo.18558930},
  url={https://zenodo.org/record/18558930}
}
```

See `CITATION.cff` for alternative formats.

## License
MIT.

## HelioMind Index

- Run `poetry run python scripts/build_heliomind_index.py --dry-run` to visualize the metric.
- Use `--output data/processed/heliomind_index.parquet` or `.json/.csv` to persist to data lake.

## HRV + Mood Pipeline

- Run `scripts/ingest_wesad.py --skip-download --extract-to <dir> --output data/processed/hrv_mood_wesad.csv` to process local WESAD files.
- Adjust `--window-minutes` and `--min-samples` parameters as needed (default 5min / 30 samples).
- Detailed specifications in `docs/HRV_MOOD_SPEC.md`.


## Núcleo em Sounio

O núcleo de cálculo está reescrito em [Sounio](https://github.com/Sounio-lang/sounio) (`sio/`) e validado
pelo **ADR-009** (*verified foreign reference*) e pelo ADR-008 (gêmeo Sounio). O Python continua no repositório,
mas só como **corroboração** (`make corroborate`): nunca é juiz. Especificação única de onde todas as
implementações saem: [`docs/SIO_CORE_SPEC.md`](docs/SIO_CORE_SPEC.md).

```bash
make toolchains   # instala .NET 9.0.300, Futhark 0.27.1, F* 2026.09.27 e o Sounio (commit pinado) sem root
make sio-test     # souc check + testes .sio + gate do gêmeo + F#/Futhark + provas F* + inventário
make corroborate  # relatório Python x Sounio (só relatório; nunca falha)
make bench        # tempos no OMNI2 completo; make lean-single: divergências Madaros x lean_single
```

### O que foi portado

| módulo | arquivo | conteúdo |
|---|---|---|
| a | `sio/omni.sio` | parser OMNI2 `.dat` (colunas 12/15/16/23/24/28/38/40, fills → ausente, Kp ÷ 10 na leitura) |
| b | `sio/swpc.sio` | 4 feeds SWPC (Kp 3 h, Dst Kyoto objeto e tabela legada, RTSW só `active == true`, `time_tag` sem fuso = UTC) |
| c | `sio/helio_index.sio` | HelioMind Index: janelas de 12 h **por tempo**, componentes em [0,1], score estrito, classe, alertas |
| d | `sio/atlas.sio` | assinaturas diária/mensal/trimestral; `storm_hours` = horas com Kp ≥ 5 |
| e | `sio/calibration.sio` | p99 por interpolação linear sobre os 52 608 registros (alvos 9.0 / 78 / 8.7 / 7.30 nPa / 1.57) |
| f | `sio/passport.sio` | correlação cruzada 0..lag_max e p-valor de permutação (blocos de 24 h, B = 1000, SplitMix64) |
| g | `sio/meta.sio` | DerSimonian–Laird; variância do efeito combinado propagada pelo GUM em **uma** função (KL-11) |

Coleta de dados é tooling (`scripts/collect_raw.sh`: só `curl`, nenhum cálculo). **Ausente nunca vira 0**: cada
valor tem um bit de validade; um agregado sem amostra válida é ausente e torna o score `indisponivel`.

### O que NÃO foi portado

Streamlit (dashboard), TFT/PatchTST (previsão neural), PCMCI+ (descoberta causal), ingestão WESAD e o pipeline
HRV+humor. Motivo: não são núcleo de cálculo verificável por oráculo e dependem de bibliotecas (torch, tigramite)
sem equivalente em Sounio. O alinhamento HRV × solar do passaporte também fica de fora: o módulo `f` recebe
séries já alinhadas.

### Tabela de oráculos (`oracles/claim_oracle_inventory.tsv`)

| módulo | gêmeo Sounio (`sio/twin/`, ADR-008) | referência `verified_foreign_reference` (ADR-009) | motivo de o gêmeo não bastar |
|---|---|---|---|
| c HelioMind | janela por idade, Dst por `max(-x,0)`, Kahan, std em duas passadas × Welford | **F#** (`oracles/fsharp`, .NET 9.0.300) | nucleo e gêmeo compartilham a semântica de f64 do compilador e a leitura das constantes |
| c invariantes | — | **F\*** 2026.09.27 (`oracles/fstar`): componentes ∈ [0,1], score monotônico, `ensure_kp_scale` idempotente com imagem em [0,9], `storm_hours ≤ valid_hours` | são invariantes de TODA entrada, o gêmeo só vê exemplos |
| d atlas | endereçamento direto por índice de período × varredura com mudança de chave | (F\*: `storm_hours ≤ valid_hours`) | — |
| e calibração | quickselect × ordenação completa; dois ponteiros × varredura para trás | **F#** (p99 e o parser OMNI próprio) | idem c |
| f passaporte | produto de z-scores × somas centradas | **Futhark** 0.27.1 (`oracles/futhark`): fluxo SplitMix64 exato **e** a distribuição nula com outro PRNG (PCG-XSH-RR, B = 20 000) | o gêmeo usa o mesmo PRNG: um erro de especificação do PRNG seria compartilhado |
| g meta | forma matricial (`P = W − W11ᵀW/s`, Gauss–Jordan) × fórmula de momentos | **F#** | idem c |
| a, b | — (parsers de formato) | — (fixtures escritas à mão + gravações reais; `jq` independente) | — |

Python (`tests/corroboration/`) é `external_corroboration_only`: reporta divergências numa tabela e nunca falha.
Uma divergência que gêmeo e referência confirmam como acerto do Sounio vira issue aqui, não ajuste no Sounio
(foi o caso de agourakis82/darwin-heliobiology#3, `_latest_timestamp`, corrigido no próprio Python).

### Limites do ambiente e da linguagem

* `spdf.gsfc.nasa.gov` não é alcançável da máquina de desenvolvimento: o OMNI2 usado no gate é a mesma série
  re-serializada no layout `.dat` a partir do parquet versionado (`data/raw/omni2_recon/`, ver o README lá).
  `scripts/collect_raw.sh omni2` baixa o arquivo real onde houver rota (`OMNI_DAT=…` no gate).
* `u64` do Madaros tem `>>` aritmético em parâmetros de função e `>` com sinal: SplitMix64 é feito em `i64`.
* `measure()` dentro de laço dá variância 0 em silêncio: o GUM de `meta.sio` é desenrolado (≤ 12 estudos).
* Um `struct` chamado `Box` sombreia o builtin e dá SIGSEGV; Madaros não exige os efeitos `IO`/`Mut` que o
  `lean_single` exige (declaramos todos). Issues: Sounio-lang/sounio#2825–#2835.
