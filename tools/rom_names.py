#!/usr/bin/env python3
"""
card_names_patcher.py — Build & inject the translated card-name list into the PocketStation ROM/save,
then fix up each card's Name Offset in the stat index and update the block count header.

Manifest (cards.json) keys used:
  - card_index_offset     ROM address where the stat index begins; first card is at +0x04
  - card_name_offset      ROM address where the new name list will be injected
  - card_lookup_address   ROM address where the 4-byte pointer to the name list is stored
  - remap                 list of {unicode, hex} mappings for character encoding
  - <language>            list of {number, name} for cards 1..722

Process:
  - Select language list (e.g., "english") and encode via remap.
  - Build name blob: [FA 21] + name1 + 00 + name2 + 00 + … + name722 + 00
  - Pad blob with 0xFF to the next 0x2000 boundary.
  - Inject at card_name_offset; update 722 Name Offsets in the stat index.
  - Write Card Name Lookup Pointer at card_lookup_address to (0x02000000 + card_name_offset).
  - Update the header Block Count byte at ROM 0x03 based on effective content size
    (filesize minus any external/container header): ceil((len(file)-baseOffset)/0x2000).

CLI mirrors rom_patches.py (minus irrelevant flags):

  Required:
    -f / --file
    -m / --manifest         (cards.json path)
    -l / --language

  Mutually exclusive ROM base-offset group (applies to all ROM-relative addresses):
    --raw                   Base offset = 0x00
    --mcs                   Base offset = 0x80
    -o / --offset OFFSET    Manually specify another header size

  Other:
    --dry-run               No write; print planned patches
    -v / --verbose          Extra logging

NOTE: No automatic backup is made. Modify in place only.
"""

import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple

POCKETSTATION_MEM_BASE = 0x02000000
TITLE_BLOCK_COUNT_OFFSET = 0x03   # ROM-relative
BLOCK_SIZE = 0x2000               # 8 KiB

EXPECTED_CARD_COUNT = 722
NAME_MARKER = bytes([0xFA, 0x21])
CARD_ENTRY_SIZE = 6
CARD_INDEX_HEADER_SIZE = 4  # bytes at card_index_offset before first card

# ----------------------------- helpers -----------------------------

def parseHexInt(text: str) -> int:
    text = text.strip()
    if text.lower().startswith('0x'):
        return int(text, 16)
    return int(text, 10)

def loadCardsJson(path: Path) -> Dict:
    with path.open('r', encoding='utf-8') as f:
        return json.load(f)

def buildRemapTable(cardsJson: Dict) -> Dict[str, int]:
    remapList = cardsJson.get('remap', [])
    table: Dict[str, int] = {}
    for entry in remapList:
        uni = entry.get('unicode', '')
        hx = entry.get('hex')
        if hx is None:
            continue
        table[uni] = int(hx, 16)
    return table

def normalizeName(name: str) -> str:
    replacements = {
        '’': "'",
        '‘': "'",
        '“': '"',
        '”': '"',
        '–': '-',
        '—': '-',
        '＃': '#',
        '№': '#',
        '　': ' ',
    }
    out = []
    for ch in name:
        out.append(replacements.get(ch, ch))
    return ''.join(out)

def encodeName(name: str, remap: Dict[str, int], strict: bool = True) -> bytes:
    name = normalizeName(name)
    out = bytearray()
    missing: Dict[str, int] = {}
    for ch in name:
        if ch in remap:
            out.append(remap[ch])
        else:
            if strict:
                missing[ch] = missing.get(ch, 0) + 1
            else:
                code = ord(ch)
                out.append(code if 0x20 <= code <= 0x7E else 0x20)
    if strict and missing:
        items = ', '.join([f"{repr(k)}×{v}" for k, v in sorted(missing.items())])
        raise ValueError(f"Unmapped characters in name {name!r}: {items}")
    return bytes(out)

def buildNameBlobAndOffsets(names: List[str], remap: Dict[str, int]) -> Tuple[bytes, List[int]]:
    """
    Returns (blob, offsets) where offsets[i] is the start offset (from the beginning of the blob)
    of the i-th card's name, except card 1 is a special case and will be 0x0000 by spec.
    """
    buf = bytearray()
    buf += NAME_MARKER

    offsets: List[int] = [0] * EXPECTED_CARD_COUNT  # card 1 forced to 0

    for i, name in enumerate(names):
        start = len(buf)
        if i > 0:
            offsets[i] = start  # card 2..722: real name start
        enc = encodeName(name, remap, strict=True)
        buf += enc + b'\x00'

    # Pad to 0x2000 boundary with 0xFF
    pad = (-len(buf)) % BLOCK_SIZE
    if pad:
        buf += bytes([0xFF]) * pad

    return bytes(buf), offsets

def computeBlockCount(effectiveSize: int) -> int:
    return (effectiveSize + BLOCK_SIZE - 1) // BLOCK_SIZE

def readRom(path: Path) -> bytearray:
    data = path.read_bytes()
    return bytearray(data)

def writeRom(path: Path, data: bytes) -> None:
    path.write_bytes(data)

def patchCardIndexNameOffsets(rom: bytearray, fileFirstCardOffset: int, nameOffsetsInBlob: List[int]) -> None:
    """
    Each card entry is 6 bytes; Name Offset is the last 2 bytes, little-endian.
    fileFirstCardOffset is FILE offset of the FIRST CARD (card_index_offset + 4 + baseOffset).
    """
    for i in range(EXPECTED_CARD_COUNT):
        entryBase = fileFirstCardOffset + (i * CARD_ENTRY_SIZE)
        nameOffPos = entryBase + 4
        val = nameOffsetsInBlob[i] & 0xFFFF
        rom[nameOffPos] = (val & 0xFF)
        rom[nameOffPos + 1] = ((val >> 8) & 0xFF)

def setCardNamePointer(rom: bytearray, filePointerOffset: int, cardNameRomOffset: int) -> None:
    """
    Writes little-endian pointer at filePointerOffset to POCKETSTATION_MEM_BASE + cardNameRomOffset.
    filePointerOffset is FILE offset (baseOffset + ROM pointer address). The pointer value uses ROM coords.
    Example ENG pointer: 00 80 00 02 for 0x02008000.
    """
    ptr = POCKETSTATION_MEM_BASE + cardNameRomOffset
    rom[filePointerOffset + 0] = (ptr & 0xFF)
    rom[filePointerOffset + 1] = ((ptr >> 8) & 0xFF)
    rom[filePointerOffset + 2] = ((ptr >> 16) & 0xFF)
    rom[filePointerOffset + 3] = ((ptr >> 24) & 0xFF)

def ensureRomSize(rom: bytearray, requiredSize: int) -> None:
    if len(rom) < requiredSize:
        rom.extend(b'\xFF' * (requiredSize - len(rom)))

def injectBlob(rom: bytearray, fileAt: int, blob: bytes) -> None:
    end = fileAt + len(blob)
    ensureRomSize(rom, end)
    rom[fileAt:end] = blob

def updateBlockCountHeader(rom: bytearray, fileHeaderBlockCountPos: int, effectiveSize: int) -> int:
    """
    effectiveSize excludes any container/header (i.e., len(rom) - baseOffset).
    fileHeaderBlockCountPos is FILE offset (baseOffset + TITLE_BLOCK_COUNT_OFFSET).
    """
    newBlocks = computeBlockCount(effectiveSize)
    rom[fileHeaderBlockCountPos] = newBlocks & 0xFF
    return newBlocks

def loadLanguageNames(cardsJson: Dict, language: str) -> List[str]:
    if language not in cardsJson:
        raise KeyError(f"Language '{language}' not found in cards.json.")
    items = cardsJson[language]
    # Expect list of {"number": int, "name": str}
    byNum = {}
    for item in items:
        num = int(item['number'])
        byNum[num] = item['name']
    names: List[str] = []
    for num in range(1, EXPECTED_CARD_COUNT + 1):
        if num not in byNum:
            raise ValueError(f"Missing name for card number {num} in language '{language}'.")
        names.append(byNum[num])
    return names

# ----------------------------- main flow -----------------------------

def main():
    ap = argparse.ArgumentParser(
        description="Build & inject translated card names into ROM/save; update index name offsets and block count."
    )

    # Required (match rom_patches.py style)
    ap.add_argument('-f', '--file', required=True, help='Save/ROM file path')
    ap.add_argument('-m', '--manifest', required=True, help='Manifest JSON file path (cards.json)')
    ap.add_argument('-l', '--language', required=True, help='Manifest Language Key (e.g., english, european, spanish, etc)')

    # Optional arguments (visual group)
    opt = ap.add_argument_group("Optional arguments")

    # Mutually exclusive base-offset group: --raw | --mcs | -o/--offset
    base = opt.add_mutually_exclusive_group()
    base.add_argument('--raw', action='store_true', help='RAW Save/ROM, Base offset = 0x00')
    base.add_argument('--mcs', action='store_true', help='MCS Headered Save/ROM, Base offset = 0x80')
    base.add_argument('-o', '--offset', help='Other Headered Save/ROM')

    # Other flags comparable to rom_patches.py
    opt.add_argument('--dry-run', action='store_true', help='Show planned patches without modifying the file')
    opt.add_argument('-v', '--verbose', action='store_true', help='Verbose logging')

    args = ap.parse_args()

    romPath = Path(args.file)
    jsonPath = Path(args.manifest)
    language = args.language

    # Determine base offset
    if args.raw:
        baseOffset = 0x00
    elif args.mcs:
        baseOffset = 0x80
    elif args.offset:
        baseOffset = parseHexInt(args.offset)
    else:
        baseOffset = 0x00

    cardsJson = loadCardsJson(jsonPath)

    # Pull mandatory ROM-relative values from manifest
    try:
        cardIndexRomOffset = parseHexInt(cardsJson['card_index_offset'])
        cardNameRomOffset  = parseHexInt(cardsJson['card_name_offset'])
        cardLookupRomAddr  = parseHexInt(cardsJson['card_lookup_address'])
    except KeyError as e:
        raise KeyError(f"Missing required key in manifest: {e}. Expected keys: "
                       f"'card_index_offset', 'card_name_offset', 'card_lookup_address'.")

    # Compute FILE offsets (where we actually write)
    fileCardIndexOffset      = baseOffset + cardIndexRomOffset
    fileFirstCardOffset      = fileCardIndexOffset + CARD_INDEX_HEADER_SIZE  # +0x04 to skip header
    fileCardNameOffset       = baseOffset + cardNameRomOffset
    filePointerOffset        = baseOffset + cardLookupRomAddr
    fileBlockCountPos        = baseOffset + TITLE_BLOCK_COUNT_OFFSET

    # Build remap and names
    remap = buildRemapTable(cardsJson)
    names = loadLanguageNames(cardsJson, language)

    # Construct blob and gather offsets (relative to start of blob)
    blob, nameOffsets = buildNameBlobAndOffsets(names, remap)

    if args.verbose:
        print(f"[i] Language: {language}")
        print(f"[i] Base offset: 0x{baseOffset:04X}")
        print(f"[i] Name blob size (post-pad): 0x{len(blob):X} ({len(blob)} bytes)")
        print(f"[i] First 16 blob bytes: {blob[:16].hex(' ').upper()}")
        print(f"[i] ROM: Index @ 0x{cardIndexRomOffset:04X} (first card @ 0x{cardIndexRomOffset + CARD_INDEX_HEADER_SIZE:04X}), Names @ 0x{cardNameRomOffset:04X}, LookupPtr @ 0x{cardLookupRomAddr:04X}")
        print(f"[i] FILE: Index @ 0x{fileCardIndexOffset:04X} (first card @ 0x{fileFirstCardOffset:04X}), Names @ 0x{fileCardNameOffset:04X}, Ptr @ 0x{filePointerOffset:04X}")

        # Optional sanity check of the 4-byte header (should often be 7F 00 00 00 per your note)
        hdr = readRom(romPath)[:0]  # noop to keep function visible in scope
        romPeek = Path(romPath).read_bytes()
        if len(romPeek) >= fileCardIndexOffset + CARD_INDEX_HEADER_SIZE:
            headVal = romPeek[fileCardIndexOffset:fileCardIndexOffset + CARD_INDEX_HEADER_SIZE]
            print(f"[i] Stat index 4-byte header @ FILE 0x{fileCardIndexOffset:04X}: {headVal.hex(' ').upper()}")

    # Load ROM
    rom = readRom(romPath)

    # Planned effective content size (excluding header)
    plannedEndFile = max(len(rom), fileCardNameOffset + len(blob))
    plannedEffectiveSize = max(plannedEndFile - baseOffset, 0)
    plannedBlocks = computeBlockCount(plannedEffectiveSize)

    # Summarize planned writes
    print("Planned patches:")
    print(f"  • Inject name blob ({len(blob)} bytes) at FILE 0x{fileCardNameOffset:04X} (ROM 0x{cardNameRomOffset:04X}).")
    print(f"  • Update pointer at FILE 0x{filePointerOffset:04X} (ROM 0x{cardLookupRomAddr:04X}) to 0x{(POCKETSTATION_MEM_BASE + cardNameRomOffset):08X}.")
    print(f"  • Rewrite {EXPECTED_CARD_COUNT} name offsets starting at FIRST CARD FILE 0x{fileFirstCardOffset:04X} (ROM 0x{cardIndexRomOffset + CARD_INDEX_HEADER_SIZE:04X}).")
    print(f"  • Update Block Count @ FILE 0x{fileBlockCountPos:02X} (ROM 0x{TITLE_BLOCK_COUNT_OFFSET:02X}) to {plannedBlocks} (for effective size {plannedEffectiveSize} bytes).")

    if args.dry_run:
        print("[dry-run] No changes written.")
        return

    # Apply blob, index rewrites, and pointer
    injectBlob(rom, fileCardNameOffset, blob)
    patchCardIndexNameOffsets(rom, fileFirstCardOffset, nameOffsets)
    setCardNamePointer(rom, filePointerOffset, cardNameRomOffset)

    # Ensure file large enough then compute effective size & update block count
    if len(rom) < plannedEndFile:
        rom.extend(b'\xFF' * (plannedEndFile - len(rom)))

    effectiveSize = max(len(rom) - baseOffset, 0)
    finalBlocks = updateBlockCountHeader(rom, fileBlockCountPos, effectiveSize)

    # In-place only
    writeRom(romPath, bytes(rom))

    print(f"[done] Wrote {romPath} (file size={len(rom)} bytes, effective={effectiveSize} bytes, blocks={finalBlocks}).")

if __name__ == "__main__":
    main()