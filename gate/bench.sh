#!/usr/bin/env bash
# Tempos (tempo de parede, inclui partida do processo e leitura/parse do arquivo) no OMNI2 completo
# (52 608 horas, 20 MB). Mediana de 3 execucoes. Sai em build/gate/bench.md.
source "$(dirname "$0")/lib.sh"
check_souc; build_fsharp; need futhark; need bc
bash gate/prepare.sh >/dev/null
OM="${OMNI_DAT#"$ROOT"/}"
median() { sort -n | sed -n 2p; }
timeit() { # cmd... ; imprime segundos
  local t0 t1; t0=$(date +%s.%N); "$@" >/dev/null 2>&1; t1=$(date +%s.%N); echo "$(echo "$t1 - $t0" | bc -l)"; }
bench3() { local a b c; a=$(timeit "$@"); b=$(timeit "$@"); c=$(timeit "$@"); printf '%s\n%s\n%s\n' "$a" "$b" "$c" | median; }
elf() { local which=$1 cmdfile=$2; cp "$cmdfile" build/gate/cmd.txt; ./build/gate/drv_$which.elf; }
fs()  { GATE_CMD="$1" dotnet "$FSHARP_DLL" run; }
fut() { GATE_CMD="$1" bash oracles/futhark/run.sh; }

echo "omni $OM" > build/gate/b_omni.txt
echo "calib $OM" > build/gate/b_calib.txt
echo "atlas monthly $OM" > build/gate/b_atlas.txt
PASS_OMNI_B=100 OMNI_DAT="$OMNI_DAT" bash gate/gen_cases.sh
echo "passport build/gate/cases/pass_omni.txt" > build/gate/b_pass.txt
# aquece caches do Futhark (compilacao fora da medida)
GATE_CMD=build/gate/b_pass.txt bash oracles/futhark/run.sh >/dev/null 2>&1 || true

{
echo "| tarefa (OMNI2 2020-2025, 52 608 h) | Sounio principal | Sounio gemeo | F# (.NET 9.0.300) | Futhark 0.27.1 (c) |"
echo "|---|---|---|---|---|"
printf '| parse OMNI2 + resumo | %.2f s | — | — | — |\n' "$(bench3 elf main build/gate/b_omni.txt)"
printf '| calibração p99 (5 séries + kp_var) | %.2f s | %.2f s | %.2f s | — |\n' \
  "$(bench3 elf main build/gate/b_calib.txt)" "$(bench3 elf twin build/gate/b_calib.txt)" "$(bench3 fs build/gate/b_calib.txt)"
printf '| atlas mensal (72 períodos) | %.2f s | %.2f s | — | — |\n' \
  "$(bench3 elf main build/gate/b_atlas.txt)" "$(bench3 elf twin build/gate/b_atlas.txt)"
printf '| passaporte: n=52 608, lags 0..72, B=100 | %.2f s | %.2f s | — | %.2f s |\n' \
  "$(bench3 elf main build/gate/b_pass.txt)" "$(bench3 elf twin build/gate/b_pass.txt)" "$(bench3 fut build/gate/b_pass.txt)"
} | tee build/gate/bench.md
