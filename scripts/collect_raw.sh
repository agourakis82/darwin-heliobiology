#!/usr/bin/env bash
# Coleta de feeds CRUS (apenas curl). Nenhum cálculo aqui: o cálculo vive em sio/.
#   NOAA SWPC -> data/raw/swpc/*.json      (HTTPS, sem credencial)
#   NASA OMNI2 -> data/raw/omni2/omni2_YYYY.dat (HTTPS; ver nota de rede em README)
# Uso: scripts/collect_raw.sh [swpc|omni2|all]
set -euo pipefail
cd "$(dirname "$0")/.."
what="${1:-all}"
SWPC=https://services.swpc.noaa.gov
OMNI=https://spdf.gsfc.nasa.gov/pub/data/omni/low_res_omni

swpc() {
  mkdir -p data/raw/swpc
  curl -fsS --retry 3 --max-time 120 "$SWPC/products/noaa-planetary-k-index.json" -o data/raw/swpc/kp_3h.json
  curl -fsS --retry 3 --max-time 120 "$SWPC/products/kyoto-dst.json"              -o data/raw/swpc/dst_kyoto.json
  curl -fsS --retry 3 --max-time 120 "$SWPC/json/rtsw/rtsw_mag_1m.json"           -o data/raw/swpc/rtsw_mag_1m.json
  curl -fsS --retry 3 --max-time 120 "$SWPC/json/rtsw/rtsw_wind_1m.json"          -o data/raw/swpc/rtsw_wind_1m.json
  sha256sum data/raw/swpc/*.json
}

omni2() {
  mkdir -p data/raw/omni2
  for y in 2020 2021 2022 2023 2024 2025; do
    curl -fsS --retry 3 --max-time 300 "$OMNI/omni2_$y.dat" -o "data/raw/omni2/omni2_$y.dat"
  done
  sha256sum data/raw/omni2/*.dat
}

case "$what" in
  swpc) swpc ;;
  omni2) omni2 ;;
  all) swpc; omni2 ;;
  *) echo "uso: $0 [swpc|omni2|all]" >&2; exit 2 ;;
esac
