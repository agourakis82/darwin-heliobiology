#!/usr/bin/env bash
# Instala em ~/.local/opt (sem root) os toolchains EXATOS de gate/toolchains.env:
#   .NET SDK 9.0.300, Futhark 0.27.1, F* 2026.09.27 (Z3 vem empacotado) e clona o Sounio no commit pinado.
# Idempotente. Precisa de: curl, tar, xz, gcc (Futhark backend c) e, para os releases do GitHub, gh OU curl.
set -euo pipefail
cd "$(dirname "$0")/.."
source gate/toolchains.env
TC="${TOOLCHAINS_DIR:-$HOME/.local/opt}"; mkdir -p "$TC/toolchains"
gh_asset() { # repo tag asset out
  if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then gh release download "$2" -R "$1" -p "$3" -O "$4" --clobber
  else curl -fsSL "https://github.com/$1/releases/download/$2/$3" -o "$4"; fi
}
# --- .NET SDK ---------------------------------------------------------------------------------
if [ "$("$TC/dotnet/dotnet" --version 2>/dev/null || true)" != "$DOTNET_SDK_VERSION" ]; then
  curl -fsSL https://dot.net/v1/dotnet-install.sh -o "$TC/dotnet-install.sh"
  bash "$TC/dotnet-install.sh" --version "$DOTNET_SDK_VERSION" --install-dir "$TC/dotnet"
fi
# --- Futhark ----------------------------------------------------------------------------------
if [ "$("$TC/toolchains/futhark/bin/futhark" --version 2>/dev/null | head -1 | awk '{print $2}' | sed 's/\.$//')" != "$FUTHARK_VERSION" ]; then
  gh_asset diku-dk/futhark "v$FUTHARK_VERSION" "futhark-$FUTHARK_VERSION-linux-x86_64.tar.xz" "$TC/toolchains/futhark.tar.xz"
  mkdir -p "$TC/toolchains/futhark"; tar xJf "$TC/toolchains/futhark.tar.xz" -C "$TC/toolchains/futhark" --strip-components=1
fi
# --- F* ---------------------------------------------------------------------------------------
if [ "$("$TC/toolchains/fstar/fstar/bin/fstar.exe" --version 2>/dev/null | head -1)" != "F* $FSTAR_VERSION" ]; then
  gh_asset FStarLang/FStar "$FSTAR_TAG" "fstar-$FSTAR_TAG-Linux-x86_64.tar.gz" "$TC/toolchains/fstar.tar.gz"
  mkdir -p "$TC/toolchains/fstar"; tar xzf "$TC/toolchains/fstar.tar.gz" -C "$TC/toolchains/fstar"
fi
# --- Sounio (bin/souc = Madaros) no commit pinado --------------------------------------------
SOUNIO_DIR="${SOUNIO_DIR:-$PWD/../work/sounio-ref}"
if [ ! -d "$SOUNIO_DIR" ]; then
  mkdir -p "$(dirname "$SOUNIO_DIR")"
  git clone --filter=blob:none "$SOUNIO_REPO_URL" "$SOUNIO_DIR"
fi
git -C "$SOUNIO_DIR" fetch --quiet origin "$SOUNIO_COMMIT" 2>/dev/null || git -C "$SOUNIO_DIR" fetch --quiet origin
git -C "$SOUNIO_DIR" checkout --quiet --detach "$SOUNIO_COMMIT"
echo "toolchains prontos: dotnet $DOTNET_SDK_VERSION, futhark $FUTHARK_VERSION, F* $FSTAR_VERSION, sounio $SOUNIO_COMMIT"
