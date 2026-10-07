#!/usr/bin/env bash
# Gate das referencias estrangeiras verificadas (ADR-009): F# (HelioMind, calibracao p99, DL) e
# Futhark (permutacao do passaporte: fluxo SplitMix64 exato + distribuicao nula com outro PRNG).
source "$(dirname "$0")/lib.sh"
check_souc; build_fsharp; need futhark
bash gate/prepare.sh
OM="${OMNI_DAT#"$ROOT"/}"
: > build/gate/timings.tsv.tmp
tm() { local t0 t1; t0=$(date +%s.%N); "$@"; t1=$(date +%s.%N); echo "$(echo "$t1 - $t0" | bc -l)"; }

# ---------------- F#: helio / calib / meta ----------------------------------------------------
sed "s#@OMNI@#$OM#g" gate/cmds_common.txt | grep -v '^#' > build/gate/cmds_fs.txt
run_driver build/gate/drv_main.elf build/gate/cmds_fs.txt build/gate/fs_main.out
cp build/gate/cmds_fs.txt build/gate/cmd.txt
fs_t=$(tm env GATE_CMD=build/gate/cmds_fs.txt bash -c "dotnet '$FSHARP_DLL' run > build/gate/fs_fsharp.out")
echo "F#: $(grep -c '^begin' build/gate/fs_fsharp.out) blocos"
fsharp compare build/gate/fs_main.out build/gate/fs_fsharp.out gate/tolerances.tsv > build/gate/fs_compare.log 2>&1 || true
tail -2 build/gate/fs_compare.log | cut -c1-300
grep -q '^AGREE' build/gate/fs_compare.log || fail "Sounio principal x F# divergem"

# ---------------- Futhark: permutacao do passaporte ------------------------------------------
for c in pass_2400; do
  echo "passport build/gate/cases/$c.txt" > build/gate/cmds_fut.txt
  run_driver build/gate/drv_main.elf build/gate/cmds_fut.txt build/gate/fut_main_$c.out
  GATE_CMD=build/gate/cmds_fut.txt bash oracles/futhark/run.sh > build/gate/fut_fut_$c.out 2>build/gate/fut_$c.log
  fsharp compare build/gate/fut_main_$c.out build/gate/fut_fut_$c.out gate/tolerances.tsv > build/gate/fut_compare_$c.log 2>&1 || true
  tail -1 build/gate/fut_compare_$c.log | cut -c1-200
  grep -q '^AGREE' build/gate/fut_compare_$c.log || fail "Sounio principal x Futhark (fluxo compartilhado) divergem em $c"
done
# distribuicao nula: quantis do Sounio (B=1000) devem cair na banda do ECDF do Futhark (outro PRNG, B=20000)
tok2dec() { awk -v t="$1" 'BEGIN{ s=substr(t,1,1); i=index(t,"p"); n=substr(t,2,i-2)+0; e=substr(t,i+1)+0; v=n*2^(e-52); printf "%.17g", (s=="-")?-v:v }'; }
q50=$(awk '$1=="null_q50"{print $2}' build/gate/fut_main_pass_2400.out); q90=$(awk '$1=="null_q90"{print $2}' build/gate/fut_main_pass_2400.out)
q95=$(awk '$1=="null_q95"{print $2}' build/gate/fut_main_pass_2400.out); q99=$(awk '$1=="null_q99"{print $2}' build/gate/fut_main_pass_2400.out)
x50=$(tok2dec "$q50"); x90=$(tok2dec "$q90"); x95=$(tok2dec "$q95"); x99=$(tok2dec "$q99")
echo "passport_dist build/gate/cases/pass_2400.txt 20000 $x50 $x90 $x95 $x99" > build/gate/cmds_dist.txt
GATE_CMD=build/gate/cmds_dist.txt bash oracles/futhark/run.sh > build/gate/fut_dist.out
cat build/gate/fut_dist.out | grep -E '^(own_B|own_q|own_ecdf)'
i=0
for p in 0.5 0.9 0.95 0.99; do
  F=$(awk -v k=$((i+1)) '$1=="own_ecdf"{c++; if(c==k) print $3}' build/gate/fut_dist.out)
  fsharp band "$p" "$F" 1000 20000 4 || fail "quantil nulo q$p fora da banda do Futhark"
  i=$((i+1))
done
echo "FOREIGN_GATE_OK"
