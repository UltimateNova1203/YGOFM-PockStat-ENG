#!/usr/bin/env bash
# decompile.sh — wrapper to extract resources for inspection.
# Order:
#   1) rom_graphics.py  --file FILE --manifest GRAPHICS --extract
#   2) gfx_convert.py   --manifest GRAPHICS --extract
#
# Usage:
#   ./decompile.sh -f FILE [-g GRAPHICS.json]
set -euo pipefail

Bold=$'\e[1m'; Red=$'\e[31m'; Green=$'\e[32m'; Yellow=$'\e[33m'; Blue=$'\e[34m'; Reset=$'\e[0m'
logInfo()  { printf "%s[i]%s %s\n" "$Blue" "$Reset" "$*"; }
logWarn()  { printf "%s[!]%s %s\n" "$Yellow" "$Reset" "$*"; }
logErr()   { printf "%s[x]%s %s\n" "$Red" "$Reset" "$*"; }
logOk()    { printf "%s[OK]%s %s\n" "$Green" "$Reset" "$*"; }

ScriptDir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"

GfxConvertPy=""
RomGraphicsPy=""

resolveTools() {
  local cand
  for cand in "$ScriptDir/tools/rom_graphics.py" "$ScriptDir/../tools/rom_graphics.py" "rom_graphics.py"; do
    [[ -f "$cand" || "$cand" == "rom_graphics.py" ]] && { RomGraphicsPy="$cand"; break; }
  done
  for cand in "$ScriptDir/tools/gfx_convert.py" "$ScriptDir/../tools/gfx_convert.py" "gfx_convert.py"; do
    [[ -f "$cand" || "$cand" == "gfx_convert.py" ]] && { GfxConvertPy="$cand"; break; }
  done
}

PythonBin=""
findPython3() {
  local candidates=("python3" "python" "/usr/bin/python3" "/opt/homebrew/bin/python3" "/usr/local/bin/python3")
  for b in "${candidates[@]}"; do
    if command -v "$b" >/dev/null 2>&1; then
      if "$b" - <<'PY' >/dev/null 2>&1
import sys
sys.exit(0 if sys.version_info >= (3,7) else 1)
PY
      then
        PythonBin="$b"
        return 0
      fi
    fi
  done
  return 1
}

printUsage() {
  cat <<USAGE
${Bold}Usage:${Reset} ./decompile.sh -f FILE [-g GRAPHICS.json]

Options:
  -f, --file FILE            Source save/ROM file
  -g, --graphics-manifest    Path to graphics.json (default: ./manifests/graphics.json)
  -h, --help                 Show this help
USAGE
}

FilePath=""
GraphicsManifest="./manifests/graphics.json"

parseArgs() {
  if [[ $# -eq 0 ]]; then printUsage; exit 1; fi
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -f|--file) FilePath="$2"; shift 2 ;;
      -g|--graphics-manifest) GraphicsManifest="$2"; shift 2 ;;
      -h|--help) printUsage; exit 0 ;;
      *) logWarn "Unknown arg: $1"; shift ;;
    esac
  done
}

validate() {
  [[ -n "$FilePath" ]] || { logErr "Missing -f/--file"; exit 1; }
  [[ -f "$FilePath" ]] || { logErr "File not found: $FilePath"; exit 1; }
  [[ -f "$GraphicsManifest" ]] || { logErr "Missing graphics manifest: $GraphicsManifest"; exit 1; }
}

main() {
  resolveTools
  parseArgs "$@"
  validate

  logInfo "Locating Python 3..."
  if ! findPython3; then logErr "Python 3.7+ not found."; exit 1; fi
  logOk "Using Python: $PythonBin"

  logInfo "Step 1/2: rom_graphics.py --extract"
  "$PythonBin" "$RomGraphicsPy" --file "$FilePath" --manifest "$GraphicsManifest" --extract

  logInfo "Step 2/2: gfx_convert.py --extract"
  "$PythonBin" "$GfxConvertPy" --manifest "$GraphicsManifest" --extract

  logOk "Decompile completed for ${Bold}${FilePath}${Reset}."
}

main "$@"
