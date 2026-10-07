#!/usr/bin/env bash
# Provas F* (ADR-009): propriedades para TODA entrada + controle negativo (as provas nao sao vacuas).
source "$(dirname "$0")/lib.sh"
need fstar.exe
[ "$(fstar.exe --version | head -1)" = "F* $FSTAR_VERSION" ] || fail "F*: esperado $FSTAR_VERSION"
bash oracles/fstar/check.sh | tee build/gate/fstar.log | tail -22
grep -q 'All verification conditions discharged successfully' build/gate/fstar.log || fail "F* nao verificou"
bash oracles/fstar/check.sh --negative | tail -3
echo "FSTAR_GATE_OK"
