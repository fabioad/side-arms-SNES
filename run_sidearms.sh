#!/usr/bin/env bash
# Roda Side Arms - Hyper Dyne (sidearms.zip) no MAME.
# Uso: ./run_sidearms.sh [opções extras do mame]
# Ex.: ./run_sidearms.sh -window -nofilter

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROM="$SCRIPT_DIR/sidearms.zip"

if [[ ! -f "$ROM" ]]; then
    echo "Erro: $ROM não encontrado." >&2
    exit 1
fi

if ! command -v mame >/dev/null 2>&1; then
    echo "Erro: mame não encontrado no PATH." >&2
    exit 1
fi

exec mame -rompath "$SCRIPT_DIR" sidearms "$@"
