#!/usr/bin/env bash
# compile.sh — wrapper to build a translated PocketStation save/ROM.
# Order:
#   1) gfx_convert.py   --manifest GRAPHICS --pack
#   2) rom_graphics.py  --file FILE --manifest GRAPHICS --pack
#   3) rom_patches.py   --file FILE --manifest PATCHES --language LANG [base-offset]
#   4) rom_names.py     --file FILE --manifest CARDS   --language LANG [base-offset]
#
# Usage:
#   ./compile.sh -f FILE [-l LANG] [--raw | --mcs | --offset HEX]
#                [-g GRAPHICS.json] [-p PATCHES.json] [-c CARDS.json] [--dry-run]
#
# Notes:
#   • Modifies FILE in place (backup handled elsewhere).
#   • Prompts for language from CARDS manifest if -l not given.
set -euo pipefail

# ---------- styling (ASCII only) ----------
Bold=$'\e[1m'; Dim=$'\e[2m'; Red=$'\e[31m'; Green=$'\e[32m'; Yellow=$'\e[33m'; Blue=$'\e[34m'; Reset=$'\e[0m'
logInfo()  { printf "%s[i]%s %s\n" "$Blue" "$Reset" "$*"; }
logWarn()  { printf "%s[!]%s %s\n" "$Yellow" "$Reset" "$*"; }
logErr()   { printf "%s[x]%s %s\n" "$Red" "$Reset" "$*"; }
logOk()    { printf "%s[OK]%s %s\n" "$Green" "$Reset" "$*"; }

printUsage() {
  cat <<USAGE
${Bold}Usage:${Reset} ./compile.sh -f FILE [-l LANG] [--raw | --mcs | --offset HEX]
                         [-g GRAPHICS.json] [-p PATCHES.json] [-c CARDS.json] [--dry-run]

Required:
  -f, --file FILE            Target save/ROM file (modified in place)

Optional:
  -l, --language LANG        Language key (if omitted, you will be prompted from CARDS manifest)
      --raw                  Base offset = 0x00
      --mcs                  Base offset = 0x80
      --offset HEX           Custom base offset (e.g., 0x100)
  -g, --graphics-manifest    Path to graphics.json (default: ./manifests/graphics.json)
  -p, --patches-manifest     Path to patches.json (default: ./manifests/patches.json)
  -c, --cards-manifest       Path to cards.json (default: ./manifests/cards.json)
      --dry-run              Print plan for patch steps (3 & 4) only
  -h, --help                 Show this help
USAGE
}

ScriptDir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"

GfxConvertPy=""
RomGraphicsPy=""
RomPatchesPy=""
RomNamesPy=""

resolveTools() {
  local cand
  # Priority: alongside this script -> ../tools -> PATH
  for cand in "$ScriptDir/tools/gfx_convert.py" "$ScriptDir/../tools/gfx_convert.py" "gfx_convert.py"; do
    [[ -f "$cand" || "$cand" == "gfx_convert.py" ]] && { GfxConvertPy="$cand"; break; }
  done
  for cand in "$ScriptDir/tools/rom_graphics.py" "$ScriptDir/../tools/rom_graphics.py" "rom_graphics.py"; do
    [[ -f "$cand" || "$cand" == "rom_graphics.py" ]] && { RomGraphicsPy="$cand"; break; }
  done
  for cand in "$ScriptDir/tools/rom_patches.py" "$ScriptDir/../tools/rom_patches.py" "rom_patches.py"; do
    [[ -f "$cand" || "$cand" == "rom_patches.py" ]] && { RomPatchesPy="$cand"; break; }
  done
  for cand in "$ScriptDir/tools/rom_names.py" "$ScriptDir/../tools/rom_names.py" "rom_names.py"; do
    [[ -f "$cand" || "$cand" == "rom_names.py" ]] && { RomNamesPy="$cand"; break; }
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

listLanguagesFromManifest() {
  "$PythonBin" - "$CardsManifest" <<'PY'
import json, sys
j = json.load(open(sys.argv[1], encoding='utf-8'))
langs = []
for k, v in j.items():
    if isinstance(v, list) and v and isinstance(v[0], dict) and 'name' in v[0] and 'number' in v[0]:
        langs.append(k)
for k in langs: print(k)
PY
}

chooseLanguage() {
  mapfile -t langs < <(listLanguagesFromManifest)
  if [[ ${#langs[@]} -eq 0 ]]; then logErr "No languages found in cards manifest."; exit 2; fi
  printf "%sLanguages in %s:%s\n" "$Bold" "$CardsManifest" "$Reset"
  local i=1; for lang in "${langs[@]}"; do printf "  %2d) %s\n" "$i" "$lang"; ((i++)); done
  local sel
  while :; do
    read -rp "Choose language [1-${#langs[@]}]: " sel
    [[ "$sel" =~ ^[0-9]+$ ]] || { logWarn "Enter a number."; continue; }
    (( sel>=1 && sel<=${#langs[@]} )) || { logWarn "Out of range."; continue; }
    Language="${langs[sel-1]}"; break
  done
  logOk "Language set to '${Language}'"
}

FilePath=""
Language=""
BaseOffsetMode="raw"; CustomOffset=""
GraphicsManifest="./manifests/graphics.json"
PatchesManifest="./manifests/patches.json"
CardsManifest="./manifests/cards.json"
DryRun="no"

parseArgs() {
  if [[ $# -eq 0 ]]; then printUsage; exit 1; fi
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -f|--file) FilePath="$2"; shift 2 ;;
      -l|--language) Language="$2"; shift 2 ;;
      --raw) BaseOffsetMode="raw"; shift ;;
      --mcs) BaseOffsetMode="mcs"; shift ;;
      --offset) BaseOffsetMode="offset"; CustomOffset="$2"; shift 2 ;;
      -g|--graphics-manifest) GraphicsManifest="$2"; shift 2 ;;
      -p|--patches-manifest)  PatchesManifest="$2"; shift 2 ;;
      -c|--cards-manifest)    CardsManifest="$2"; shift 2 ;;
      --dry-run) DryRun="yes"; shift ;;
      -h|--help) printUsage; exit 0 ;;
      *) logWarn "Unknown arg: $1"; shift ;;
    esac
  done
}

validate() {
  [[ -n "$FilePath" ]] || { logErr "Missing -f/--file"; exit 1; }
  [[ -f "$FilePath" ]] || { logErr "File not found: $FilePath"; exit 1; }
  [[ -f "$GraphicsManifest" ]] || { logErr "Missing graphics manifest: $GraphicsManifest"; exit 1; }
  [[ -f "$PatchesManifest"  ]] || { logErr "Missing patches manifest:  $PatchesManifest"; exit 1; }
  [[ -f "$CardsManifest"    ]] || { logErr "Missing cards manifest:    $CardsManifest"; exit 1; }
}

computeBaseOffsetArgs() {
  case "$BaseOffsetMode" in
    raw)   BaseArgs=(--raw) ;;
    mcs)   BaseArgs=(--mcs) ;;
    offset) BaseArgs=(--offset "$CustomOffset") ;;
  esac
}

copyTexturesIfPresent() {
  if [[ -d "./textures" && -d "./gfx/png" ]]; then
    logInfo "Copying textures/*.png -> ./gfx/png/"
    shopt -s nullglob
    cp ./textures/*.png ./gfx/png/ || true
    shopt -u nullglob
  fi
}

main() {
  resolveTools
  parseArgs "$@"
  validate

  logInfo "Locating Python 3..."
  if ! findPython3; then logErr "Python 3.7+ not found."; exit 1; fi
  logOk "Using Python: $PythonBin"

  if [[ -z "$Language" ]]; then
    chooseLanguage
  else
    logOk "Language set to '${Language}'"
  fi

  computeBaseOffsetArgs
  [[ "$DryRun" == "yes" ]] && DryArg=(--dry-run) || DryArg=()

  copyTexturesIfPresent

  logInfo "Step 1/4: gfx_convert.py --pack"
  "$PythonBin" "$GfxConvertPy" --manifest "$GraphicsManifest" --pack

  logInfo "Step 2/4: rom_graphics.py --pack"
  "$PythonBin" "$RomGraphicsPy" --file "$FilePath" --manifest "$GraphicsManifest" --pack

  logInfo "Step 3/4: rom_patches.py"
  "$PythonBin" "$RomPatchesPy" --file "$FilePath" --manifest "$PatchesManifest" --language "$Language" "${BaseArgs[@]}" "${DryArg[@]}"

  logInfo "Step 4/4: rom_names.py"
  "$PythonBin" "$RomNamesPy" --file "$FilePath" --manifest "$CardsManifest"   --language "$Language" "${BaseArgs[@]}" "${DryArg[@]}"

  logOk "Compile completed for ${Bold}${FilePath}${Reset}."
}

main "$@"
