
#!/usr/bin/env python3
"""
gfx_tool.py — unified extractor/packer for PocketStation/PS1 graphics binaries.

Reads asset definitions from a graphics.json file and either:
  - extract: dump raw bitmap/sequence binaries to ./gfx/bin (or override)
  - pack:    write raw bitmap/sequence binaries from ./gfx/bin back into a ROM/save

Assumptions (kept intentionally simple):
  - Bitmaps are stored as 1-bit-per-pixel, row-major, 8 pixels per byte.
  - Size of a single bitmap defaults to ceil(width*height/8). You may override with
    "size" in graphics.json per asset. For "sequence", "step" is the byte distance
    between consecutive bitmaps (defaults to size when omitted).
  - Addresses in graphics.json are byte offsets relative to a base offset. Use --raw,
    --mcs, or --offset to choose the base adjustment.
  - Only assets with "active": true are processed unless --include-inactive is given.

graphics.json schema (per asset):
  {
    "name": "title",
    "addr": "0x63C8",
    "width": 32,
    "height": 16,
    "kind": "bitmap" | "sequence",
    "count": 8,          # sequence only
    "step": "0x80",      # optional; byte step between frames; defaults to size
    "size": 64,          # optional; override bytes per bitmap
    "active": true
  }

Usage examples:
  Extract (MCS headered save):
    python3 gfx_tool.py --rom BASLUSP01411-YUGIOH.gme --manifest graphics.json --extract --mcs

  Pack (RAW save at offset 0x00) with a custom gfx dir:
    python3 gfx_tool.py --rom save.bin --manifest graphics.json --pack --raw --out ./mygfx

  Pack with a custom base offset (hex) and only one asset:
    python3 gfx_tool.py --rom save.gme --manifest graphics.json --pack --offset 0x80 --only title
"""
import argparse, json, math, os, pathlib, sys, shutil


def resolve_bin_dir(path_str: str) -> str:
    """Treat the provided directory as a *parent* directory.
    If it already ends with '/bin', use as-is; otherwise append '/bin'.
    """
    p = pathlib.Path(path_str)
    if p.name == 'bin':
        return str(p)
    return str(p / 'bin')


def parse_hex_or_int(s):
    if isinstance(s, int):
        return s
    s = str(s).strip().lower()
    if s.startswith('0x'):
        return int(s, 16)
    return int(s, 10)

def bytes_per_bitmap(asset):
    if 'size' in asset:
        return int(asset['size'])
    w = int(asset['width'])
    h = int(asset['height'])
    # 1bpp, row-major, 8 pixels per byte
    return (w * h + 7) // 8

def step_for(asset, size):
    if 'step' in asset:
        return parse_hex_or_int(asset['step'])
    return size

def load_graphics_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if isinstance(data, dict) and 'assets' in data:
        return data['assets']
    if isinstance(data, list):
        return data
    raise ValueError("graphics.json must be a list of assets or an object with an 'assets' list.")

def safe_mkdir(p):
    pathlib.Path(p).mkdir(parents=True, exist_ok=True)

def extract_asset(rom_bytes, base_offset, asset, out_dir):
    size = bytes_per_bitmap(asset)
    addr = parse_hex_or_int(asset['addr'])
    start = base_offset + addr
    kind = asset['kind']
    name = asset['name']
    if kind == 'bitmap':
        chunk = rom_bytes[start:start+size]
        out_path = os.path.join(out_dir, f"{name}.bin")
        with open(out_path, 'wb') as f:
            f.write(chunk)
        return [out_path]
    elif kind == 'sequence':
        count = int(asset.get('count', 0))
        if count <= 0:
            raise ValueError(f"Asset '{name}' is a sequence but has no valid 'count'.")
        step = step_for(asset, size)
        written = []
        for i in range(count):
            offs = start + i * step
            chunk = rom_bytes[offs:offs+size]
            out_path = os.path.join(out_dir, f"{name}_{i:03d}.bin")
            with open(out_path, 'wb') as f:
                f.write(chunk)
            written.append(out_path)
        return written
    else:
        raise ValueError(f"Unknown kind '{kind}' for asset '{name}'.")

def read_bin_or_warn(path, expected_size):
    with open(path, 'rb') as f:
        data = f.read()
    if len(data) != expected_size:
        # Pad or truncate with a warning-like print
        if len(data) < expected_size:
            print(f"Note: {path} is {len(data)}B; padding to {expected_size}B with 0x00")
            data = data + b'\x00' * (expected_size - len(data))
        else:
            print(f"Note: {path} is {len(data)}B; truncating to {expected_size}B")
            data = data[:expected_size]
    return data

def pack_asset(rom_bytes, base_offset, asset, out_dir):
    size = bytes_per_bitmap(asset)
    addr = parse_hex_or_int(asset['addr'])
    start = base_offset + addr
    kind = asset['kind']
    name = asset['name']

    if kind == 'bitmap':
        in_path = os.path.join(out_dir, f"{name}.bin")
        if not os.path.exists(in_path):
            print(f"Skip pack: missing {in_path}")
            return 0
        data = read_bin_or_warn(in_path, size)
        rom_bytes[start:start+size] = data
        return size

    elif kind == 'sequence':
        count = int(asset.get('count', 0))
        if count <= 0:
            raise ValueError(f"Asset '{name}' is a sequence but has no valid 'count'.")
        step = step_for(asset, size)
        total = 0
        for i in range(count):
            in_path = os.path.join(out_dir, f"{name}_{i:03d}.bin")
            if not os.path.exists(in_path):
                print(f"Skip frame {i}: missing {in_path}")
                continue
            data = read_bin_or_warn(in_path, size)
            offs = start + i * step
            rom_bytes[offs:offs+size] = data
            total += size
        return total
    else:
        raise ValueError(f"Unknown kind '{kind}' for asset '{name}'.")

def main():
    ap = argparse.ArgumentParser(
        description="Unified graphics extractor/packer using a manifest JSON (graphics/bitmaps).",
    )

    # Required options (shown in main section)
    ap.add_argument('-f', '--file', required=True, help='Save/ROM file path')
    ap.add_argument('-m', '--manifest', required=True, help='Manifest JSON file path')

    # Mode (exactly one required)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument('-e', '--extract', action='store_true', help='Extract graphics from ROM')
    mode.add_argument('-p', '--pack', action='store_true', help='Pack graphics into ROM')

    # Optional arguments (visual grouping)
    opt = ap.add_argument_group("Optional arguments")
    # Offsets (mutually exclusive but optional)
    base = opt.add_mutually_exclusive_group()
    base.add_argument('--raw', action='store_true', help='RAW Save/ROM, Base offset = 0x00')
    base.add_argument('--mcs', action='store_true', help='MCS Headered Save/ROM, Base offset = 0x80')
    base.add_argument('-o', '--offset', help='Other Headered Save/ROM')

    # Other optional args
    opt.add_argument('-d', '--directory', default='./gfx/bin', help='Override graphics binaries directory')
    opt.add_argument('--only', help='Only process the asset with this name')
    opt.add_argument('--include-inactive', action='store_true', help='Include inactive assets from manifest')

    args = ap.parse_args()

    if args.offset:
        base_offset = parse_hex_or_int(args.offset)
    elif args.mcs:
        base_offset = 0x80
    else:
        base_offset = 0x00

    assets = load_graphics_json(args.manifest)
    if args.only:
        assets = [a for a in assets if a.get('name') == args.only]

    if not args.include_inactive:
        assets = [a for a in assets if a.get('active', True)]

    if not assets:
        print("No assets to process after filters.")
        return 0

    with open(args.file, 'rb') as f:
        rom_bytes = bytearray(f.read())

    effective_dir = resolve_bin_dir(args.directory)
    safe_mkdir(effective_dir)

    if args.extract:
        total = 0
        for a in assets:
            out = extract_asset(rom_bytes, base_offset, a, effective_dir)
            total += len(out)
            print(f"Extracted {a['name']}: {len(out)} file(s)")
        print(f"Done. Extracted {total} file(s) to {effective_dir}")
    else:
        # pack
        total_bytes = 0
        for a in assets:
            written = pack_asset(rom_bytes, base_offset, a, effective_dir)
            print(f"Packed {a['name']}: {written} bytes")
            total_bytes += written
        with open(args.file, 'wb') as f:
            f.write(rom_bytes)
        print(f"Done. Wrote {total_bytes} bytes into {args.file}")
    return 0

if __name__ == '__main__':
    sys.exit(main())
