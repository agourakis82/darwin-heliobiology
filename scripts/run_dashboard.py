"""Script para executar o HelioMind Dashboard."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> None:
    """Executa o dashboard Streamlit."""
    # Caminho para o app.py
    app_path = Path(__file__).parent.parent / "src" / "darwin_heliobiology" / "dashboard" / "app.py"

    if not app_path.exists():
        print(f"Erro: arquivo app.py não encontrado em {app_path}", file=sys.stderr)
        sys.exit(1)

    # Executar streamlit run
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
    ]

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Erro ao executar o dashboard: {e}", file=sys.stderr)
        sys.exit(e.returncode)


if __name__ == "__main__":
    main()
