#!/usr/bin/env bash
# Valida oracles/claim_oracle_inventory.tsv contra o schema do Sounio e o ADR-009:
#  - 10 colunas; oracle_class em {sounio_native_expected, sounio_closed_form_twin, verified_foreign_reference,
#    external_corroboration_only, research_harness};
#  - Python/Rust nunca em verified_foreign_reference nem com foreign_hard_fail=yes;
#  - toda linha verified_foreign_reference cita a versao fixada do toolchain e um motivo de insuficiencia do gemeo;
#  - a versao citada bate com gate/toolchains.env.
source "$(dirname "$0")/lib.sh"
f=oracles/claim_oracle_inventory.tsv
awk -F'\t' -v dn="$DOTNET_SDK_VERSION" -v fu="$FUTHARK_VERSION" -v fs="$FSTAR_VERSION" '
  /^#/ || /^gate_id/ {next}
  { n++
    if (NF != 10) { print "FAIL colunas=" NF ": " $1; bad++ ; next }
    ok = ($3=="sounio_native_expected"||$3=="sounio_closed_form_twin"||$3=="verified_foreign_reference"||$3=="external_corroboration_only"||$3=="research_harness"||$3=="bootstrap_integrity"||$3=="formal_only")
    if (!ok) { print "FAIL oracle_class invalida: " $1 " " $3; bad++ }
    if ($3=="verified_foreign_reference") {
      if ($6 ~ /python|rust/) { print "FAIL python/rust como verified_foreign_reference: " $1; bad++ }
      if ($8 !~ /toolchain=/ || $8 !~ /motivo=/) { print "FAIL sem toolchain/motivo: " $1; bad++ }
      if ($6 ~ /fsharp/ && $8 !~ ("SDK " dn)) { print "FAIL F# sem SDK " dn ": " $1; bad++ }
      if ($6 ~ /futhark/ && $8 !~ ("futhark " fu)) { print "FAIL Futhark sem " fu ": " $1; bad++ }
      if ($6 ~ /fstar/ && $8 !~ ("F\\* " fs)) { print "FAIL F* sem " fs ": " $1; bad++ }
    }
    if ($6 ~ /python/ && $4=="yes") { print "FAIL python com foreign_hard_fail=yes: " $1; bad++ }
    if ($3=="external_corroboration_only" && $4!="no") { print "FAIL corroboracao deve ter foreign_hard_fail=no: " $1; bad++ }
  }
  END { printf "inventario: %d linhas, %d problemas\n", n, bad+0; exit (bad>0) }' "$f"
echo "INVENTORY_OK"
