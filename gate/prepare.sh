#!/usr/bin/env bash
# Prepara dados e binarios do gate: OMNI (xz -> build/data), casos gerados, drivers Sounio compilados.
source "$(dirname "$0")/lib.sh"
check_souc
mkdir -p build/data
if [ ! -f "$OMNI_DAT" ]; then
  need xz
  (cd data/raw/omni2_recon && sha256sum -c SHA256SUMS >/dev/null) || fail "SHA256 de omni2_2020-2025.dat.xz nao confere"
  xz -dc data/raw/omni2_recon/omni2_2020-2025.dat.xz > "$OMNI_DAT"
fi
[ "$(wc -l < "$OMNI_DAT")" -eq 52608 ] || fail "OMNI deve ter 52608 linhas"
OMNI_DAT="$OMNI_DAT" bash gate/gen_cases.sh
for d in main twin; do
  "$SOUC" compile "sio/drv_$d.sio" -o "build/gate/drv_$d.elf" > "build/gate/compile_$d.log" 2>&1 \
    || { tail -20 "build/gate/compile_$d.log"; fail "compilacao do driver $d"; }
  if grep -Eq '^(warning|error)' "build/gate/compile_$d.log"; then fail "warning/error ao compilar drv_$d (ver build/gate/compile_$d.log)"; fi
done
echo "prepare: dados e drivers prontos ($(wc -l < "$OMNI_DAT") linhas OMNI)"
