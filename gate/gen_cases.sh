#!/usr/bin/env bash
# Gera os casos de permutacao do passaporte (entrada do gate). awk so formata e faz aritmetica
# INTEIRA exata (abaixo de 2^53); nenhum valor estatistico e calculado aqui.
set -euo pipefail
cd "$(dirname "$0")/.."
OUT=build/gate/cases; mkdir -p "$OUT"
# --- caso sintetico n=2400: x pseudo-aleatorio inteiro/1000, y = 0.3*x(i-6) + ruido ----------
awk 'BEGIN{
  n=2400; print "LAGMAX 48"; print "B 1000"; print "SEED 20261006"; print "N " n;
  for(i=0;i<n;i++) x[i]=((i*i*7919 + i*104729) % 10007)/1000.0;
  printf "X"; for(i=0;i<n;i++){ printf " %s", x[i]; if(i%24==23 && i<n-1) printf "\n+" } printf "\n";
  printf "Y"; for(i=0;i<n;i++){ v=((i*i*31 + i*17) % 997)/100.0; if(i>=6) v += 0.3*x[i-6]; printf " %s", v; if(i%24==23 && i<n-1) printf "\n+" } printf "\n" }' > "$OUT/pass_2400.txt"
# --- caso em escala OMNI: Kp*10 (col 38) e Dst (col 40), inteiros crus das 52 608 horas --------
if [ -f "${OMNI_DAT:-build/data/omni2_2020-2025.dat}" ]; then
awk -v B="${PASS_OMNI_B:-100}" 'BEGIN{ n=0 } { kp[n]=$39; dst[n]=$41; n++ } END{
  print "LAGMAX 72"; print "B " B; print "SEED 20261006"; print "N " n;
  printf "X"; for(i=0;i<n;i++){ printf " %s", kp[i]; if(i%24==23 && i<n-1) printf "\n+" } printf "\n";
  printf "Y"; for(i=0;i<n;i++){ printf " %s", dst[i]; if(i%24==23 && i<n-1) printf "\n+" } printf "\n" }' \
  "${OMNI_DAT:-build/data/omni2_2020-2025.dat}" > "$OUT/pass_omni.txt"
fi
