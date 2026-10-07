#!/usr/bin/env bash
# Verify oracles/fstar/Helio.Props.fst (ADR-009 criterion 3: toolchain pinned).
#   ./check.sh             -> proofs must verify; prints theorem list on success
#   ./check.sh --negative  -> Helio.Props.Negative.fst must be REJECTED (one error per NEG-n)
set -u
PINNED="F* 2026.09.27"
export PATH="$HOME/.local/opt/toolchains/fstar/fstar/bin:$PATH"
cd "$(dirname "$0")"

got="$(fstar.exe --version 2>/dev/null | head -n1)"
if [ "$got" != "$PINNED" ]; then
  echo "FAIL: toolchain mismatch: expected '$PINNED', got '${got:-<none>}'" >&2
  exit 2
fi
echo "$got"

THEOREMS="
clip01_in_unit_interval
component_in_unit_interval_kp
component_in_unit_interval_dst
component_in_unit_interval_bz
component_in_unit_interval_pressure
component_in_unit_interval_variability
weights_sum_to_one
weights_nonneg
score_in_unit_interval
score_monotone_kp
score_monotone_dst
score_monotone_bz
score_monotone_pressure
score_monotone_variability
ensure_kp_scale_in_range
ensure_kp_scale_idempotent
storm_hours_le_valid_hours
valid_hours_le_length
"
FSTAR_OPTS="--cache_checked_modules --cache_dir build/fstar-cache --warn_error -328"
mkdir -p build/fstar-cache

if [ "${1:-}" = "--negative" ]; then
  # Each NEG-n block is checked in isolation (prelude + block) in a scratch dir, because F*
  # stops at the first failing lemma of a module. Every block must be REJECTED.
  src=Helio.Props.Negative.fst
  tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
  total=$(grep -c '^(\* NEG-[0-9]*:' "$src")
  first=$(grep -n '^(\* NEG-1:' "$src" | cut -d: -f1)
  ok=1
  for n in $(seq 1 "$total"); do
    start=$(grep -n "^(\* NEG-$n:" "$src" | cut -d: -f1)
    next=$(grep -n "^(\* NEG-$((n+1)):" "$src" | cut -d: -f1)
    [ -z "$next" ] && next=$(( $(wc -l < "$src") + 1 ))
    { head -n $((first-1)) "$src"; sed -n "${start},$((next-1))p" "$src"; } > "$tmp/Helio.Props.Negative.fst"
    if fstar.exe --warn_error -328 "$tmp/Helio.Props.Negative.fst" >"$tmp/out$n" 2>&1; then
      echo "NOT rejected: NEG-$n (F* ACCEPTED a false lemma)" >&2; ok=0
    elif grep -q '\* Error' "$tmp/out$n"; then
      echo "rejected NEG-$n: $(grep -m1 -A1 '\* Error' "$tmp/out$n" | tr '\n' ' ' | cut -c1-110)"
    else
      echo "NEG-$n failed for a non-verification reason:" >&2; cat "$tmp/out$n" >&2; ok=0
    fi
  done
  if [ $ok -ne 1 ]; then echo "FAIL: negative control incomplete" >&2; exit 1; fi
  echo "Negative control OK: F* rejected all $total deliberately false variants"
  exit 0
fi

out="$(fstar.exe $FSTAR_OPTS Helio.Props.fst 2>&1)"; rc=$?
echo "$out"
if [ $rc -ne 0 ] || ! printf '%s\n' "$out" | grep -q 'All verification conditions discharged successfully'; then
  echo "FAIL: verification failed" >&2; exit 1
fi
for t in $THEOREMS; do echo "theorem $t"; done
exit 0
