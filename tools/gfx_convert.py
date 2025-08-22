
#!/usr/bin/env python3
"""
gfx_convert.py — Convert between 1bpp raw binaries and PNGs for assets listed in graphics.json.




Modes (choose one):
  -e, --extract   Convert .bin -> .png
  -p, --pack      Convert .png -> .bin

Optional:
  -i, --invert    Invert pixel colors during conversion (mirrors existing logic)
  -d, --directory Parent graphics directory (default: ./gfx). Subdirs are fixed:
                  ./bin and ./png underneath this directory.

Assumptions:
  - Assets are defined in ./graphics.json with fields:
      name, width, height, kind ("bitmap" or "sequence"), optional count, active
  - Filenames follow the conventions:
      bitmap   : bin/name.bin  <-> png/name.png
      sequence : bin/name_000.bin ... <-> png/name_000.png ...
  - Bit packing is MSB-first, 8 pixels per byte, row-major.
  - Only assets with active:true are processed.

Examples:
  # Extract all active assets to PNGs under ./gfx/png from ./gfx/bin
  python3 gfx_convert.py --extract

  # Pack PNGs back into BINs under ./gfx/bin
  python3 gfx_convert.py --pack

  # Use a different parent folder and invert pixel colors on conversion
  python3 gfx_convert.py --extract --invert --directory ./art
"""

# --- Per-8x8-tile horizontal mirroring helpers (bit-level) ---
def _build_reverse_table():
    tbl = [0]*256
    for b in range(256):
        v = b
        v = ((v & 0xF0) >> 4) | ((v & 0x0F) << 4)
        v = ((v & 0xCC) >> 2) | ((v & 0x33) << 2)
        v = ((v & 0xAA) >> 1) | ((v & 0x55) << 1)
        tbl[b] = v
    return tbl

_REVERSE_TABLE = _build_reverse_table()

def reverseByte(b: int) -> int:
    return _REVERSE_TABLE[b & 0xFF]

def mirror8x8TileBytes(tile: bytes) -> bytes:
    if len(tile) != 8:
        raise ValueError(f"Expected 8 bytes for an 8x8 tile, got {len(tile)}")
    return bytes(reverseByte(x) for x in tile)
# --- end mirroring helpers ---


import argparse, json, os, sys, pathlib

try:
    from PIL import Image
except Exception as e:
    print("Pillow (PIL) is required. Please install with: pip install Pillow", file=sys.stderr)
    raise

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def load_manifest(path='graphics.json'):
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if isinstance(data, dict) and 'assets' in data:
        return data['assets']
    if isinstance(data, list):
        return data
    raise ValueError("graphics.json must be a list of assets or an object with an 'assets' list.")

def ensure_dirs(parent_dir):
    bin_dir = os.path.join(parent_dir, 'bin')
    png_dir = os.path.join(parent_dir, 'png')
    pathlib.Path(bin_dir).mkdir(parents=True, exist_ok=True)
    pathlib.Path(png_dir).mkdir(parents=True, exist_ok=True)
    return bin_dir, png_dir

def _unpack_1bpp_to_pixels(data: bytes, w: int, h: int, invert: bool):
    """Return a list/bytes of 0 or 255 per pixel, length w*h. MSB-first per byte."""
    total = w * h
    out = bytearray(total)
    for i in range(total):
        byte = data[i >> 3]
        bit = 7 - (i & 7)
        v = (byte >> bit) & 1
        if invert:
            v ^= 1
        # By convention: 1 = black pixel (0), 0 = white (255)
        out[i] = 0 if v else 255
    return out

def _pack_pixels_to_1bpp(img: Image.Image, invert: bool) -> bytes:
    """Threshold image to 1bpp and pack MSB-first, returning bytes."""
    # Convert to grayscale then threshold at 128
    g = img.convert('L')
    w, h = g.size
    px = g.tobytes()
    total = w * h
    out_len = (total + 7) // 8
    out = bytearray(out_len)
    for i in range(total):
        v = 1 if px[i] < 128 else 0  # darker -> 1 (black)
        if invert:
            v ^= 1
        if v:
            out[i >> 3] |= (1 << (7 - (i & 7)))
    return bytes(out)

def _save_png(pixels, w, h, path):
    img = Image.frombytes('L', (w, h), bytes(pixels))
    # Convert to 1-bit palette with white/black to keep small
    img = img.convert('1')  # dithering off by default
    img.save(path)

# -----------------------------------------------------------------------------
# Core conversion per asset
# -----------------------------------------------------------------------------

def convert_bitmap_extract(bin_path, png_path, w, h, invert):
    if not os.path.exists(bin_path):
        return False, f"Missing {bin_path}"
    with open(bin_path, 'rb') as f:
        data = f.read()
    expected = (w * h + 7) // 8
    if len(data) < expected:
        # pad missing bytes
        data = data + b'\x00' * (expected - len(data))
    elif len(data) > expected:
        data = data[:expected]

    # Per 8x8 tile: mirror by reversing bit order within each 8-pixel row byte
    data = bytes(reverseByte(b) for b in data)
    pixels = _unpack_1bpp_to_pixels(data, w, h, invert=invert)
    _save_png(pixels, w, h, png_path)
    return True, f"{png_path}"

def convert_bitmap_pack(png_path, bin_path, w, h, invert):
    if not os.path.exists(png_path):
        return False, f"Missing {png_path}"
    img = Image.open(png_path)
    if img.size != (w, h):
        img = img.resize((w, h), resample=Image.NEAREST)
    data = _pack_pixels_to_1bpp(img, invert=invert)
    # Mirror per-tile horizontally: reverse bits in each byte
    data = bytes(reverseByte(b) for b in data)

    with open(bin_path, 'wb') as f:
        f.write(data)
    return True, f"{bin_path}"

# -----------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="Graphics converter using a manifest JSON (graphics/bitmaps). Converts between 1bpp BIN and PNG."
    )
    # Required manifest
    ap.add_argument('-m', '--manifest', required=True, help='Manifest JSON file path')

    # Mode (exactly one required)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument('-e', '--extract', action='store_true', help='Extract graphics from BIN to PNG')
    mode.add_argument('-p', '--pack', action='store_true', help='Pack graphics from PNG to BIN')

    # Optional arguments group
    opt = ap.add_argument_group("Optional")
    opt.add_argument('-i', '--invert', action='store_true', help='Invert pixel colors during conversion')
    opt.add_argument('-d', '--directory', default='./gfx', help='Override graphics binaries directory')
    opt.add_argument('--only', help='Only process the asset with this name')
    opt.add_argument('--include-inactive', action='store_true', help='Include inactive assets from manifest')

    args = ap.parse_args()
    assets = load_manifest(args.manifest)

    # Only active by default
    if not args.include_inactive:
        assets = [a for a in assets if a.get('active', True) or args.include_inactive]
    if args.only:
        assets = [a for a in assets if a.get('name') == args.only]
    if args.only:
        assets = [a for a in assets if a.get('name') == args.only]

    bin_dir, png_dir = ensure_dirs(args.directory)

    converted = 0
    skipped = 0
    messages = []

    for a in assets:
        name = a['name']
        w = int(a['width'])
        h = int(a['height'])
        kind = a['kind']

        if kind == 'bitmap':
            bin_path = os.path.join(bin_dir, f"{name}.bin")
            png_path = os.path.join(png_dir, f"{name}.png")
            if args.extract:
                ok, msg = convert_bitmap_extract(bin_path, png_path, w, h, args.invert)
            else:
                ok, msg = convert_bitmap_pack(png_path, bin_path, w, h, args.invert)
            if ok:
                converted += 1
            else:
                skipped += 1
            messages.append(msg)

        elif kind == 'sequence':
            count = int(a.get('count', 0))
            if count <= 0:
                messages.append(f"Skip {name}: sequence without valid 'count'")
                skipped += 1
                continue
            for i in range(count):
                base = f"{name}_{i:03d}"
                bin_path = os.path.join(bin_dir, f"{base}.bin")
                png_path = os.path.join(png_dir, f"{base}.png")
                if args.extract:
                    ok, msg = convert_bitmap_extract(bin_path, png_path, w, h, args.invert)
                else:
                    ok, msg = convert_bitmap_pack(png_path, bin_path, w, h, args.invert)
                if ok:
                    converted += 1
                else:
                    skipped += 1
                messages.append(msg)
        else:
            messages.append(f"Unknown kind for {name}: {kind}")
            skipped += 1

    for m in messages:
        print(m)
    print(f"Done. Converted {converted}, skipped {skipped}.")
    return 0

if __name__ == '__main__':
    sys.exit(main())
