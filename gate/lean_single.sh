#!/usr/bin/env bash
# Roda os testes .sio e os drivers do gate tambem sob SOUNIO_SOUC_ENGINE=lean_single e REPORTA
# divergencias Madaros x lean_single (nao e hard-fail: cada divergencia vira issue em
# Sounio-lang/sounio com o programa minimo, ver docs/divergences/).
# lean_single resolve `use` relativo ao CWD (Madaros: relativo ao arquivo de entrada; D08), entao
# rodamos de uma arvore espelho build/lean/ com os modulos na raiz e symlinks para dados/fixtures.
source "$(dirname "$0")/lib.sh"
check_souc; build_fsharp
L=build/lean; rm -rf "$L"; mkdir -p "$L/build/gate"
cp sio/*.sio "$L/"; cp -r sio/twin "$L/twin"
ln -s ../../tests "$L/tests"; ln -s ../../../build/data "$L/build/data"; ln -s ../../../build/gate/cases "$L/build/gate/cases"
export SOUNIO_SOUC_ENGINE=lean_single
rep=build/gate/lean_single_report.txt; : > "$rep"
for t in "$L"/test_*.sio; do
  n=$(basename "$t")
  out="$(cd "$L" && "$SOUC" run "$n" 2>&1)" && rc=0 || rc=$?
  s=$(grep -E '^[A-Z0-9_]+_OK$' <<<"$out" | tail -1 || true)
  if [ $rc -eq 0 ] && [ -n "$s" ]; then echo "lean_single ok   $n $s" | tee -a "$rep"
  else echo "lean_single DIVERGE $n rc=$rc $(grep -E "^error" <<<"$out" | head -2 | tr "\n" " " || true)" | tee -a "$rep"; fi
done
# drivers: mesma lista de comandos; comparar saida lean_single x Madaros com o comparador F#
# D09: lean_single trunca read_file em 16 MiB; para isolar OUTRAS divergencias comparamos num recorte
# do OMNI (40 000 linhas ~ 15,3 MB) e reportamos a truncagem do arquivo inteiro a parte.
head -n 40000 "$OMNI_DAT" > build/data/omni_lt16mib.dat
sed "s#@OMNI@#build/data/omni_lt16mib.dat#g" gate/cmds_common.txt gate/cmds_sounio_only.txt | grep -v '^#' > build/gate/cmds_lean.txt
run_driver build/gate/drv_main.elf build/gate/cmds_lean.txt build/gate/ref_main.out
cp build/gate/cmds_lean.txt build/gate/cmd.txt
for d in main twin; do
  if (cd "$L" && "$SOUC" compile "drv_$d.sio" -o "../gate/drv_${d}_lean.elf" > "../gate/compile_${d}_lean.log" 2>&1); then
    chmod +x build/gate/drv_${d}_lean.elf; ./build/gate/drv_${d}_lean.elf > build/gate/lean_$d.out 2>build/gate/lean_$d.err && lrc=0 || lrc=$?
    echo "lean_single driver $d: rc=$lrc blocos=$(grep -c '^begin' build/gate/lean_$d.out)" | tee -a "$rep"
    if [ "$d" = main ]; then fsharp compare build/gate/ref_main.out build/gate/lean_main.out gate/tolerances.tsv > build/gate/lean_compare_main.log 2>&1 || true
       echo "lean_single x Madaros (drv main): $(grep -cE '^(MISMATCH|STRUCTURE)' build/gate/lean_compare_main.log) divergencias; veredito $(tail -1 build/gate/lean_compare_main.log)" | tee -a "$rep"; fi
  else
    echo "lean_single DIVERGE compilar drv_$d: $(grep -E '^error' build/gate/compile_${d}_lean.log | head -2 | tr '\n' ' ')" | tee -a "$rep"
  fi
done
# arquivo inteiro (20 MB): documenta D09
cp build/gate/cmds_lean.txt /dev/null
printf 'calib %s\natlas monthly %s\n' "build/data/omni2_2020-2025.dat" "build/data/omni2_2020-2025.dat" > build/gate/cmds_full.txt
cp build/gate/cmds_full.txt build/gate/cmd.txt
chmod +x build/gate/drv_main_lean.elf
./build/gate/drv_main_lean.elf > build/gate/lean_full.out 2>/dev/null || true
echo "lean_single arquivo inteiro (D09): $(awk '/^n_records/{print "n_records="$2; exit}' build/gate/lean_full.out) (Madaros: 52608)" | tee -a "$rep"
exit 0
