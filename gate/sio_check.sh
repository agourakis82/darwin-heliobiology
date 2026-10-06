#!/usr/bin/env bash
# `souc check` em todo arquivo .sio de sio/. Falha em rc != 0, em ausencia de "check: OK" e em
# qualquer linha warning/error (o Madaros trata nome inexistente como warning: `check` verde
# nao basta).
source "$(dirname "$0")/lib.sh"
check_souc
n=0; bad=0
while IFS= read -r f; do
  n=$((n+1))
  out="$("$SOUC" check "$f" 2>&1)" && rc=0 || rc=$?
  if [ $rc -ne 0 ] || ! grep -q '^check: OK' <<<"$out" || grep -Eq '^(warning|error)' <<<"$out"; then
    echo "FAIL check $f (rc=$rc)"; echo "$out" | grep -E '^(warning|error)|^ +=' | head -8; bad=$((bad+1))
  else
    echo "ok   check $f"
  fi
done < <(find sio -name '*.sio' | sort)
echo "souc check: $((n-bad))/$n arquivos limpos"
[ $bad -eq 0 ] || exit 1
