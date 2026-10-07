#!/usr/bin/env bash
# Gate-protocol driver (docs/SIO_CORE_SPEC.md §1) for the Futhark oracle.
#
# Commands handled (others in the command file are skipped silently):
#   passport <case-file>
#   passport_dist <case-file> <B_own> <x1> <x2> <x3> <x4>     (thresholds as plain decimals)
#
# Reads build/gate/cmd.txt (cwd = repo root).  GATE_CMD overrides: if it names an
# existing file it is used as the command file, otherwise its value is taken as
# the literal command line(s).  BUILD_DIR (default build/futhark) holds the cached
# compiled binary; it is rebuilt only when passport.fut is newer.
#
# awk/sed are used ONLY to re-format text (case file -> Futhark text input,
# Futhark output -> protocol lines).  No arithmetic on data values happens here.
# Toolchain pinned: Futhark 0.27.1, `c` backend.
set -euo pipefail

export PATH="$HOME/.local/opt/toolchains/futhark/bin:$PATH"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$HERE/passport.fut"
BUILD_DIR="${BUILD_DIR:-build/futhark}"
BIN="$BUILD_DIR/passport"
FUTHARK_PIN="0.27.1"

ver="$(futhark --version | head -1 | awk '{print $2}' | sed -E 's/[^0-9.].*//; s/\.$//')"
if [ "$ver" != "$FUTHARK_PIN" ]; then
  echo "run.sh: Futhark $ver found, $FUTHARK_PIN required" >&2; exit 2
fi

mkdir -p "$BUILD_DIR"
if [ ! -x "$BIN" ] || [ "$SRC" -nt "$BIN" ]; then
  futhark c "$SRC" -o "$BIN" >&2
fi

# ---- case file -> Futhark text input (x, y, lag_max, B, seed) ---------------
# usage: case_to_input <case> <B_override|""> ; prints Futhark input on stdout
case_to_input() {
  awk -v bov="$2" '
    function flush_arr(name,   a, i, out) { }
    {
      if ($0 ~ /^[ \t]*$/) next
      if ($0 ~ /^\+/) { line = substr($0, 2); cur_append = 1 }
      else { line = $0; cur_append = 0 }
      n = split(line, t, /[ \t]+/)
      start = 1
      if (!cur_append) { key = t[1]; if (key == "") { key = t[2]; start = 3 } else start = 2 }
      else if (t[1] == "") start = 2
      if (key == "X" || key == "Y") {
        for (i = start; i <= n; i++) if (t[i] != "") { arr[key] = arr[key] (arr[key] == "" ? "" : ",") t[i] "f64" }
      } else if (!cur_append) { sc[key] = t[start] }
    }
    END {
      B = (bov != "") ? bov : sc["B"]
      print "[" arr["X"] "]"
      print "[" arr["Y"] "]"
      print sc["LAGMAX"] "i64"
      print B "i64"
      print sc["SEED"] "u64"
    }' "$1"
}

# case field lookup (N) -- plain text extraction
case_field() { awk -v k="$2" '$1 == k { print $2; exit }' "$1"; }

# strip Futhark type suffixes; 0.0 -> 0 (spec token for zero)
unsuffix() {
  sed -E 's/(f64|i64|u64)//g' | sed -E 's/^0\.0$/0/'
}

run_passport() {
  local case="$1" tmp
  tmp="$(mktemp "$BUILD_DIR/in.XXXXXX")"
  case_to_input "$case" "" > "$tmp"
  echo "n $(case_field "$case" N)"
  "$BIN" -e shared_full < "$tmp" | awk '
    BEGIN { split("T_obs lag_obs p null_q50 null_q90 null_q95 null_q99", lab, " ") }
    NR <= 7 { v[NR] = $0; next }
    NR == 8 { arr = $0 }
    END {
      gsub(/(f64|i64|u64)/, "", arr); gsub(/[\[\] ]/, "", arr)
      for (i = 1; i <= 3; i++) { s = v[i]; gsub(/(f64|i64|u64)/, "", s); if (s == "0.0") s = "0"; print lab[i], s }
      m = split(arr, a, ",")
      for (b = 1; b <= m; b++) { s = a[b]; if (s == "0.0") s = "0"; print "null", b - 1, s }
      for (i = 4; i <= 7; i++) { s = v[i]; gsub(/(f64|i64|u64)/, "", s); if (s == "0.0") s = "0"; print lab[i], s }
    }'
  rm -f "$tmp"
}

run_passport_dist() {
  local case="$1" bown="$2"; shift 2
  local tmp xs="" x
  for x in "$@"; do xs="${xs}${xs:+,}${x}f64"; done
  tmp="$(mktemp "$BUILD_DIR/in.XXXXXX")"
  { case_to_input "$case" "$bown"; echo "[$xs]"; } > "$tmp"
  echo "own_B $bown"
  "$BIN" -e own < "$tmp" | awk -v xl="$*" '
    NR <= 4 { s = $0; gsub(/(f64|i64|u64)/, "", s); if (s == "0.0") s = "0"; v[NR] = s; next }
    NR == 5 { arr = $0 }
    END {
      split("50 90 95 99", q, " ")
      for (i = 1; i <= 4; i++) print "own_q" q[i], v[i]
      gsub(/(f64|i64|u64)/, "", arr); gsub(/[\[\] ]/, "", arr)
      m = split(arr, a, ","); split(xl, xx, " ")
      for (i = 1; i <= m; i++) { s = a[i]; if (s == "0.0") s = "0"; print "own_ecdf", xx[i], s }
    }'
  rm -f "$tmp"
}

# ---- command file ------------------------------------------------------------
if [ -n "${GATE_CMD:-}" ]; then
  if [ -f "$GATE_CMD" ]; then CMDSRC="$(cat "$GATE_CMD")"; else CMDSRC="$GATE_CMD"; fi
else
  CMDSRC="$(cat build/gate/cmd.txt)"
fi

while IFS= read -r raw || [ -n "$raw" ]; do
  line="${raw%%#*}"
  # shellcheck disable=SC2206
  tok=($line)
  [ "${#tok[@]}" -gt 0 ] || continue
  case "${tok[0]}" in
    passport)
      echo "begin ${tok[*]}"
      run_passport "${tok[1]}"
      echo end ;;
    passport_dist)
      echo "begin ${tok[*]}"
      run_passport_dist "${tok[1]}" "${tok[2]}" "${tok[@]:3:4}"
      echo end ;;
    *) : ;;  # not handled by this oracle
  esac
done <<< "$CMDSRC"
