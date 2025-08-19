#!/usr/bin/env python3
import sys
from pathlib import Path
import math

# Constants from your spec
ROM_BASE            = 0x02000000
NAME_LIST_ROM_ADDR  = 0x02008000
LOOKUP_PTR_ROM_ADDR = 0x02002A7C
CARD_TABLE_ROM_START= 0x02004C0C
CARD_TABLE_ROM_END  = 0x02005CF7
BYTES_PER_CARD      = 6
START_OF_TEXT       = bytes([0xFA, 0x21])  # FA 21
BLOCK_SIZE          = 0x2000               # 8 KiB
HEADER_BLOCK_BYTE   = 0x03                 # file offset 0x03 (block count)

# Derived file offsets
NAME_LIST_FILE_OFF  = NAME_LIST_ROM_ADDR - ROM_BASE
LOOKUP_PTR_FILE_OFF = LOOKUP_PTR_ROM_ADDR - ROM_BASE
CARD_TABLE_FILE_START = CARD_TABLE_ROM_START - ROM_BASE
CARD_TABLE_FILE_END   = CARD_TABLE_ROM_END   - ROM_BASE

NUM_CARDS = ((CARD_TABLE_FILE_END - CARD_TABLE_FILE_START) // BYTES_PER_CARD) + 1  # expect 722

def le16(n): return bytes([n & 0xFF, (n >> 8) & 0xFF])
def le32(n): return bytes([n & 0xFF, (n >> 8) & 0xFF, (n >> 16) & 0xFF, (n >> 24) & 0xFF])

def main():
    if len(sys.argv) != 3:
        print(f"Usage: {Path(sys.argv[0]).name} <input.gme> <Card-list.txt>")
        sys.exit(1)

    gme_path = Path(sys.argv[1])
    list_path = Path(sys.argv[2])

    if not gme_path.is_file():
        sys.exit(f"ERROR: GME not found: {gme_path}")
    if not list_path.is_file():
        sys.exit(f"ERROR: Card list not found: {list_path}")

    # Load and sanitize card names
    names = [ln.rstrip("\r\n") for ln in list_path.read_text(encoding="utf-8").splitlines()]
    # Filter accidental empties but keep order
    names = [n for n in names if n != ""]
    if len(names) != NUM_CARDS:
        sys.exit(f"ERROR: Expected {NUM_CARDS} names, got {len(names)}. (Check Card-list.txt lines/order.)")

    # Read GME
    data = bytearray(gme_path.read_bytes())

    # Ensure we can write at 0x8000
    if len(data) < NAME_LIST_FILE_OFF:
        # Extend with zeros up to name list start
        data.extend(b"\x00" * (NAME_LIST_FILE_OFF - len(data)))

    # Build the name blob: FA 21 + "Name\0" * N
    blob = bytearray()
    blob += START_OF_TEXT
    name_offsets = []  # offsets relative to the start of the blob (ROM base at 0x02008000)
    cursor = len(blob)  # first name starts after FA 21

    for idx, name in enumerate(names):
        # Note: English = ASCII-safe; fall back to Latin-1 if needed
        try:
            enc = name.encode("ascii")
        except UnicodeEncodeError:
            enc = name.encode("latin-1", errors="replace")

        if idx == 0:
            # Special rule: first card points to start of whole list (FA 21), so offset = 0
            name_offsets.append(0)
        else:
            # For others, point to the beginning of that card's name within the blob
            name_offsets.append(cursor)

        blob += enc + b"\x00"
        cursor = len(blob)

    # Sanity: make sure 16-bit offsets can hold largest offset
    if len(blob) - 1 > 0xFFFF:
        sys.exit(f"ERROR: Names blob too large ({len(blob)} bytes); 16-bit offsets would overflow.")

    # Write/overwrite the blob at 0x8000
    end_pos = NAME_LIST_FILE_OFF + len(blob)
    if len(data) < end_pos:
        data.extend(b"\x00" * (end_pos - len(data)))
    data[NAME_LIST_FILE_OFF:end_pos] = blob

    # Update the lookup pointer at 0x2A7C to 0x02008000 (little-endian)
    new_ptr = le32(NAME_LIST_ROM_ADDR)
    data[LOOKUP_PTR_FILE_OFF:LOOKUP_PTR_FILE_OFF+4] = new_ptr

    # Update each card’s 2-byte name offset inside the 6-byte record
    # The stored value is (card_name_rom_addr - NAME_LIST_ROM_ADDR), i.e. relative to the pointer.
    # Since our blob sits exactly at NAME_LIST_FILE_OFF, and ROM==FILE+ROM_BASE, the relative offset equals name_offsets[i].
    for i in range(NUM_CARDS):
        entry_off = CARD_TABLE_FILE_START + i * BYTES_PER_CARD
        name_off_field = entry_off + 4  # bytes 4..5
        rel = name_offsets[i]
        if not (0 <= rel <= 0xFFFF):
            sys.exit(f"ERROR: Relative offset for card {i+1} out of range: {rel:#x}")
        data[name_off_field:name_off_field+2] = le16(rel)

    # Pad to next 8 KiB boundary
    new_size = len(data)
    blocks = math.ceil(new_size / BLOCK_SIZE)
    padded_size = blocks * BLOCK_SIZE
    if padded_size > new_size:
        data.extend(b"\x00" * (padded_size - new_size))

    # Update block count at file offset 0x03
    if padded_size // BLOCK_SIZE > 255:
        sys.exit("ERROR: Block count exceeds 255; header single byte cannot represent it.")
    data[HEADER_BLOCK_BYTE] = blocks & 0xFF

    # Write backup then save
    backup = gme_path.with_suffix(gme_path.suffix + ".bak")
    if not backup.exists():
        backup.write_bytes(gme_path.read_bytes())
    gme_path.write_bytes(data)

    # Friendly summary
    print("OK:")
    print(f"  Wrote {len(blob)} bytes of names at 0x{NAME_LIST_FILE_OFF:05X} (ROM 0x{NAME_LIST_ROM_ADDR:08X}).")
    print(f"  Updated lookup pointer @ 0x{LOOKUP_PTR_FILE_OFF:05X} to {new_ptr.hex(' ')}.")
    print(f"  Updated {NUM_CARDS} name offsets in card table @ 0x{CARD_TABLE_FILE_START:05X}..0x{CARD_TABLE_FILE_END:05X}.")
    print(f"  Padded to {padded_size} bytes ({blocks} × 0x2000). Set header block count byte (offset 0x03) to {blocks}.")

if __name__ == "__main__":
    main()