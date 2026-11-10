#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
project_root="$PWD"
export SIDEARMS_SOURCE="${SIDEARMS_SOURCE:-$project_root/rom}"
ghidra_root="${GHIDRA_HOME:-$project_root/tools/local/ghidra_12.2_PUBLIC}"
if [[ -n "${GHIDRA_JAVA_HOME:-}" ]]; then
    export JAVA_HOME="$GHIDRA_JAVA_HOME"
elif [[ -x "$project_root/tools/local/jdk25/bin/java" ]]; then
    export JAVA_HOME="$project_root/tools/local/jdk25"
elif [[ -z "${JAVA_HOME:-}" && -x /tmp/opencode/jdk25/bin/java ]]; then
    export JAVA_HOME=/tmp/opencode/jdk25
fi
mkdir -p build/analysis build/ghidra build/tmp
python3 - <<'PY'
import sys
from pathlib import Path
sys.path.insert(0,'tools')
from arcade_source import Source
source=Source()
m=source.region('maincpu')
Path('build/analysis/bank0.bin').write_bytes(m[:0xc000])
Path('build/analysis/sound.bin').write_bytes(source.region('audiocpu'))
PY
export GHIDRA_HEADLESS_JAVA_OPTIONS="-Djava.io.tmpdir=$project_root/build/tmp -Dapplication.tempdir=$project_root/build/tmp -Dapplication.cachedir=$project_root/build/cache -Dapplication.settingsdir=$project_root/build/settings"
"$ghidra_root/support/analyzeHeadless" "$project_root/build/ghidra" SidearmsMDPort \
    -import "$project_root/build/analysis/bank0.bin" \
    -processor z80:LE:16:default -cspec default -loader BinaryLoader \
    -scriptPath "$project_root/tools/ghidra" \
    -postScript SidearmsPortAudit.java "$project_root/build/analysis" -overwrite
"$ghidra_root/support/analyzeHeadless" "$project_root/build/ghidra" SidearmsMDPort \
    -import "$project_root/build/analysis/sound.bin" \
    -processor z80:LE:16:default -cspec default -loader BinaryLoader \
    -scriptPath "$project_root/tools/ghidra" \
    -postScript SidearmsPortAudit.java "$project_root/build/analysis" -overwrite
