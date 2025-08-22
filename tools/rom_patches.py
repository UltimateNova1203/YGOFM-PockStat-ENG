#!/usr/bin/env python3
"""
rom_patches.py — apply byte patches from a language-specific manifest.

Reads a patches manifest JSON (see patches.json) and writes byte sequences into a target
ROM/save file at given addresses. You choose which language section to apply.

Manifest schema (example):
{
  "version": 1,
  "english": [
    {"name": "Save Title", "addr": "0x0004", "value": "50 6F 63 6B ...", "active": true},
    ...
  ],
  "german": [ ... ],
  ...
}

- "addr": byte offset (accepts hex like "0x2354" or integer).
- "value": either a space-separated hex string ("DE AD BE EF") or a list of bytes (ints/hex strings).
- "active": if false, the patch is skipped unless --include-inactive is given.

Usage examples:
  Dry run (show what would be patched), English set:
    python3 rom_patches.py -f BASLUSP01411-YUGIOH.gme -m patches.json -l english --dry-run

  Apply patches (write to file) for European set:
    python3 rom_patches.py -f BASLUSP01411-YUGIOH.gme -m patches.json -l european

Optional offset helpers (like other tools):
  --raw      => base offset 0x00
  --mcs      => base offset 0x80
  --offset X => custom base offset (hex or int)

"""
import argparse, json, os, pathlib, shutil, sys

def parse_hex_or_int(x):
    if isinstance(x, int):
        return x
    s = str(x).strip()
    if s.lower().startswith("0x"):
        return int(s, 16)
    return int(s, 10)

def parse_value_to_bytes(val):
    """
    Accepts either:
      - Space-separated hex string: "DE AD BE EF 00"
      - List of items: [222, "0xAD", "BE", "0xEF", 0]
    Returns: bytes
    """
    if isinstance(val, (bytes, bytearray)):
        return bytes(val)
    if isinstance(val, str):
        parts = [p for p in val.replace(",", " ").split() if p]
    elif isinstance(val, (list, tuple)):
        parts = val
    else:
        raise TypeError(f"Unsupported value type: {type(val)}")
    out = bytearray()
    for p in parts:
        if isinstance(p, int):
            out.append(p & 0xFF)
            continue
        s = str(p).strip()
        if s.lower().startswith("0x"):
            out.append(int(s, 16) & 0xFF)
        else:
            # bare hex byte
            out.append(int(s, 16) & 0xFF)
    return bytes(out)

def load_manifest(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def find_language_section(manifest, lang_key):
    # exact match first
    if lang_key in manifest:
        return manifest[lang_key]
    # case-insensitive fallback
    for k in manifest.keys():
        if k.lower() == lang_key.lower():
            return manifest[k]
    raise KeyError(f"Language '{lang_key}' not found in manifest. Available: {', '.join([k for k in manifest.keys() if k not in ('version',)])}")

def apply_patches(rom_bytes, base_offset, patches, include_inactive=False, only_name=None, dry_run=False):
    total = 0
    for entry in patches:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name", "(unnamed)")
        active = entry.get("active", True)
        if only_name and name != only_name:
            continue
        if not active and not include_inactive:
            continue
        addr = parse_hex_or_int(entry["addr"])
        data = parse_value_to_bytes(entry["value"])
        start = base_offset + addr
        end = start + len(data)
        if end > len(rom_bytes):
            raise ValueError(f"Patch '{name}' (addr=0x{addr:X}, len={len(data)}) exceeds file size ({len(rom_bytes)}).")
        if dry_run:
            print(f"[DRY] {name}: would write {len(data)}B at 0x{start:06X} (manifest addr 0x{addr:X})")
        else:
            rom_bytes[start:end] = data
            print(f"Patched {name}: wrote {len(data)}B at 0x{start:06X}")
        total += len(data)
    return total

def main():
    
    ap = argparse.ArgumentParser(
        description="Apply ROM/save patches from a language-specific manifest.",
    )

    # Required options (shown in main section)
    ap.add_argument('-f', '--file', required=True, help='Save/ROM file path')
    ap.add_argument('-m', '--manifest', required=True, help='Manifest JSON file path')
    ap.add_argument('-l', '--language', required=True, help='Manifest Language Key (e.g., english, european, spanish, etc)')

    # Optional arguments (visual grouping)
    opt = ap.add_argument_group("Optional arguments")
    # Offsets (mutually exclusive but optional)
    base = opt.add_mutually_exclusive_group()
    base.add_argument('--raw', action='store_true', help='RAW Save/ROM, Base offset = 0x00')
    base.add_argument('--mcs', action='store_true', help='MCS Headered Save/ROM, Base offset = 0x80')
    base.add_argument('-o', '--offset', help='Other Headered Save/ROM')

    # Other optional args
    opt.add_argument('--only', help='Only apply the patch with this name')
    opt.add_argument('--include-inactive', action='store_true', help='Include inactive patches from manifest')
    opt.add_argument('--dry-run', action='store_true', help='Show planned patches without modifying the file')

    args = ap.parse_args()

    if args.offset:
        base_offset = parse_hex_or_int(args.offset)
    elif args.mcs:
        base_offset = 0x80
    else:
        base_offset = 0x00  # default raw

    manifest = load_manifest(args.manifest)
    patches = find_language_section(manifest, args.language)

    with open(args.file, "rb") as f:
        rom_bytes = bytearray(f.read())

    written = apply_patches(
        rom_bytes,
        base_offset=base_offset,
        patches=patches,
        include_inactive=args.include_inactive,
        only_name=args.only,
            )

    if args.dry_run:
        print(f"Dry run complete. Would write {written} bytes in total.")
        return 0

    with open(args.file, "wb") as f:
        f.write(rom_bytes)
    print(f"Done. Wrote {written} bytes into {args.file}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
