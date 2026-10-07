#!/usr/bin/env bash
# Gate do gemeo (ADR-008 `sounio_closed_form_twin`): implementacao principal x gemeo (algoritmo
# diferente) em todos os comandos, tolerancias de gate/tolerances.tsv (padrao 1e-12 relativo).
source "$(dirname "$0")/lib.sh"
check_souc; build_fsharp
bash gate/prepare.sh
rel() { sed "s#@OMNI@#${OMNI_DAT#"$ROOT"/}#g" "$@"; }
rel gate/cmds_common.txt gate/cmds_sounio_only.txt | grep -v '^#' > build/gate/cmds_twin.txt
t0=$(date +%s.%N); run_driver build/gate/drv_main.elf build/gate/cmds_twin.txt build/gate/twin_main.out; t1=$(date +%s.%N)
run_driver build/gate/drv_twin.elf build/gate/cmds_twin.txt build/gate/twin_twin.out; t2=$(date +%s.%N)
printf 'twin_gate\tmain\t%.2f\ntwin_gate\ttwin\t%.2f\n' "$(echo "$t1 - $t0" | bc -l)" "$(echo "$t2 - $t1" | bc -l)" >> build/gate/timings.tsv
echo "blocos: principal=$(grep -c '^begin' build/gate/twin_main.out) gemeo=$(grep -c '^begin' build/gate/twin_twin.out)"
fsharp compare build/gate/twin_main.out build/gate/twin_twin.out gate/tolerances.tsv > build/gate/twin_compare.log 2>&1 || true
tail -3 build/gate/twin_compare.log | cut -c1-400
grep -q '^AGREE' build/gate/twin_compare.log || fail "principal x gemeo divergem"
echo "TWIN_GATE_OK"
