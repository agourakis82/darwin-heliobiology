#!/usr/bin/env bash
# `souc run` em todo sio/test_*.sio: exige rc 0, a linha sentinela "<NOME>_OK" e nenhum warning.
source "$(dirname "$0")/lib.sh"
check_souc
n=0; bad=0
while IFS= read -r f; do
  n=$((n+1))
  out="$("$SOUC" run "$f" 2>&1)" && rc=0 || rc=$?
  if [ $rc -ne 0 ] || ! grep -Eq '^[A-Z0-9_]+_OK$' <<<"$out" || grep -Eq '^(warning|error)' <<<"$out"; then
    echo "FAIL run $f (rc=$rc)"; echo "$out" | tail -6; bad=$((bad+1))
  else
    echo "ok   run $f  $(grep -E '^[A-Z0-9_]+_OK$' <<<"$out" | tail -1)"
  fi
done < <(find sio -name 'test_*.sio' | sort)
echo "testes .sio: $((n-bad))/$n verdes"
[ $bad -eq 0 ] || exit 1
