#!/usr/bin/env bash
# Funcoes e ambiente comuns do gate. Uso: `source gate/lib.sh` a partir da raiz do repo.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
# shellcheck disable=SC1091
source "$ROOT/gate/toolchains.env"

# --- Sounio (clone do Sounio-lang/sounio; bin/souc = Madaros) -----------------------------------
: "${SOUNIO_DIR:=$ROOT/../work/sounio-ref}"
export SOUNIO_STDLIB_PATH="$SOUNIO_DIR/stdlib"
SOUC="$SOUNIO_DIR/bin/souc"

# --- toolchains pinados (instalados por gate/install_toolchains.sh em ~/.local/opt) ------------
TC="${TOOLCHAINS_DIR:-$HOME/.local/opt}"
export DOTNET_ROOT="$TC/dotnet" DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_NOLOGO=1
export PATH="$TC/dotnet:$TC/toolchains/futhark/bin:$TC/toolchains/fstar/fstar/bin:$PATH"
FSHARP_DLL="$ROOT/oracles/fsharp/HelioOracle/bin/Release/net9.0/HelioOracle.dll"
OMNI_DAT="${OMNI_DAT:-$ROOT/build/data/omni2_2020-2025.dat}"
mkdir -p "$ROOT/build/gate"

fail() { echo "GATE FAIL: $*" >&2; exit 1; }
need() { command -v "$1" >/dev/null 2>&1 || fail "ferramenta ausente: $1 (rode gate/install_toolchains.sh)"; }

# Confere o compilador: versao exata e commit do clone.
check_souc() {
  [ -x "$SOUC" ] || fail "souc nao encontrado em $SOUC (defina SOUNIO_DIR; ver gate/toolchains.env)"
  local line
  line="$("$SOUC" --version 2>&1 | grep -E '^Madaros' | head -1 || true)"
  [ "$line" = "$SOUC_VERSION_LINE" ] || fail "souc: esperado '$SOUC_VERSION_LINE', obtido '$line'"
  if [ -d "$SOUNIO_DIR/.git" ] || [ -f "$SOUNIO_DIR/.git" ]; then
    local head
    head="$(git -C "$SOUNIO_DIR" rev-parse HEAD)"
    [ "$head" = "$SOUNIO_COMMIT" ] || echo "AVISO: clone do Sounio em $head (pin: $SOUNIO_COMMIT)" >&2
  fi
}

check_fsharp() {
  need dotnet
  [ "$(dotnet --version)" = "$DOTNET_SDK_VERSION" ] || fail "dotnet: esperado $DOTNET_SDK_VERSION, obtido $(dotnet --version)"
}

build_fsharp() {
  check_fsharp
  (cd "$ROOT/oracles/fsharp" && dotnet build HelioOracle/HelioOracle.fsproj -c Release --nologo -v quiet 2>&1 | tail -3) \
    || fail "build do oraculo F# falhou"
  [ -f "$FSHARP_DLL" ] || fail "DLL do oraculo F# ausente"
}

fsharp() { dotnet "$FSHARP_DLL" "$@"; }

# Roda um driver Sounio (ELF) com um arquivo de comandos; saida em $3.
run_driver() { # elf cmdfile out
  cp "$2" "$ROOT/build/gate/cmd.txt"
  "$1" > "$3"
}
