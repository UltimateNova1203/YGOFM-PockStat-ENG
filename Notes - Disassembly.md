# Disassembly

## Save Data Formatting

- 1 Block: 8KiB = 8192 bytes = 2000h bytes
- 1 Frame: 128 bytes = 80h bytes

### Title Frame (Block 0, Frame 0)

Check for magic byte Q, if so skip to 0x80h
Check for magic byte SC, if so mark as start of file (treat as 0x00h)

- 0x00h: Magic Byte SC (ASCII)
- 0x02h: Icon Frame Count (Min 1, Max 3) [0x11h: 1, 0x12h: 2, 0x13h: 3]
- 0x03h: Block Count (Min 1, Max 15) [0x01h: 1, 0x02h: 2, etc]
- 0x04h: Save File Name (Shift-JIS) [0x00h padded]
- 0x44h: Reserved [0x00h]
- 0x50h: Number of File View Mono Icon Frames [0x0000h: Use Exec-Icons]
- 0x52h: PocketStation Save Type ["MCX0": Normal, "MCX1": w/ Snapshot]
- 0x56h: Number of Exec-Icons [0x01h - 0xFFh]
- 0x57h: Number of BU Commands [0x00h - 0x7Fh]
- 0x58h: Reserved [0x00h]
- 0x5Ch: FLASH1 Entrypoint (in memory, offset + 0x02000000h) [bit0=THUMB]
- 0x60h: Icon 16 Color Palette Data (each entry is 16bit CLUT)

### Icon Frame (Block 0, Frame 1-3)

How many frames for Icons depends on what was set in the Title Frame. Each icon takes up 1 frame.

- 0x00h Icon Bitmap (16x16 pixel, 4-bit color depth)

### Data Frame (Block 0-X, Frame N-63)

X is how many Blocks (1 block is 0)
N is first Frame of block, after any Title or Icon frames.

## Data

### Save Title

JPN:
- 0x0004: ＰｏｃｋｅｔＳｔａｔｉｏｎ　　遊戯王　真デュエルモンスターズ

ENG:
- 0x0004: PocketStation Yu-Gi-Oh!

### Save Region

JPN:
- 0x2354: BISLPM-86398-YUGIOH

USA:
- 0x2354: BASLUS-01411-YUGIOH

### General Text

JPN:
- 0x657E: 13 1E 15 1D FB (EXIT OK?) [Main Menu]
- 0x6587: 13 1E 15 1D 00 1A 16 (EXIT OK) [Memo]
- 0x658F: 18 15 1C 1C (MISS)
- 0x6594: 19 1A FB 12 10 1D 10 (NO DATA) [Save Error]
- 0x659C: 11 1A 1B 1F FB 12 10 1D 10 (COPY DATA)
- 0x65A6: 1A 12 12 FB 12 10 1D 10 (ODD DATA)
- 0x65AF: 1F 1A 2F FB 14 13 1D 0E (YOU GET!)
- 0x65B8: 1A 19 11 13 FB 1A 19 17 1F (ONCE ONLY)

ENG:
- 0x657E: 45 58 49 54 FB 4F 4B 0F (EXIT OK?) [Main Menu]
- 0x6587: 45 58 49 54 00 4F 4B (EXIT OK) [Memo]
- 0x658F: 4D 49 53 53 (MISS)
- 0x6594: 4E 4F FB 44 41 54 41 (NO DATA) [Save Error]
- 0x659C: 43 4F 50 59 FB 44 41 54 41 (COPY DATA)
- 0x65A6: 4F 44 44 FB 44 41 54 41 (ODD DATA)
- 0x65AF: 43 41 52 44 FB 47 45 54 0E (CARD GET!)
- 0x65B8: 4F 4E 4C 59 FB 4F 4E 43 45 (ONLY ONCE)

### Card Names

- 0x2A7Ch: Card Name Lookup Pointer Address
-- JPN: 5C 34 00 02
-- ENG: 00 80 00 02

### Card Stats

#### Index

- 0x4C08h: Start of Card Stat Index [0x7F000000]
- 0x4C0Ch: Card 1 ATK (x10)
- 0x4C0Dh: Card 1 Type (and ATK/DEF high nibble)
- 0x4C0Eh: Card 1 Guardian Signs
- 0x4C0Fh: Card 1 DEF (x10)
- 0x4C10h: Card 1 Name Offset
- 0x4C12h: Card 2 ATK (x10)
- etc...

#### Card Type

ATK ≥ 2560: XOR 0x01h
DEF ≥ 2560: XOR 0x80h

| Value | Type          |
|-------|---------------|
| 0x00h | Dragon        |
| 0x02h | Spellcaster   |
| 0x04h | Zombie        |
| 0x06h | Warrior       |
| 0x08h | Beast-Warrior |
| 0x0Ah | Beast         |
| 0x0Ch | Winged Beast  |
| 0x0Eh | Fiend         |
| 0x10h | Fairy         |
| 0x12h | Insect        |
| 0x14h | Dinosaur      |
| 0x16h | Reptile       |
| 0x18h | Fish          |
| 0x1Ah | Sea Serpent   |
| 0x1Ch | Machine       |
| 0x1Eh | Thunder       |
| 0x20h | Aqua          |
| 0x22h | Pyro          |
| 0x24h | Rock          |
| 0x26h | Plant         |
| 0x28h | Magic         |
| 0x2Ah | Trap          |
| 0x2Ch | Ritual        |
| 0x2Eh | Equip         |

#### Guardian Signs

_# Primary Sign
#_ Secondary Sign

| Value | Sign    |
|-------|---------|
| 0     | None    |
| 1     | Mars    |
| 2     | Jupiter |
| 3     | Saturn  |
| 4     | Uranus  |
| 5     | Pluto   |
| 6     | Neptune |
| 7     | Mercury |
| 8     | Sun     |
| 9     | Moon    |
| A     | Venus   |

## Graphics

Chunks of 8x8 pixels are horizontally mirrored

Palette:
 -  0 = 255, 255, 255 (00 = FFFFFF)
 -  1 = 0, 0, 0 (01 = 000000)

### PocketStation Homepage Images

0x0200h: Number of PocketStation Homepage Images [0x01h: 1, 0x02h: 2 etc]
0x0202h: Reserved [0x0600h]
0x0204h: FLASH1 Entrypoint for Images
0x0208h: Reserved [0x00h]

32x32 pixel, 1bpp, 2-Dimensional:

- 0x0280h: Image 1
- 0x0300h: Image 2
- 0x0380h: Image 3
- 0x0400h: Image 4
- 0x0480h: Image 5
- 0x0500h: Image 6
- 0x0580h: Image 7
- 0x0600h: Image 8

### Alphabet (0x5CF8h)

8x8 pixel, 1bpp, 1-Dimensional:

| Address | Hex | Old | New |
|---------|-----|-----|-----|
| 0x5CF8h | 00  |     |     |
| 0x5D00h | 01  | ァ   |     |
| 0x5D08h | 02  | ィ   |     |
| 0x5D10h | 03  | ゥ   |     |
| 0x5D18h | 04  | ェ   |     |
| 0x5D20h | 05  | ォ   |     |
| 0x5D28h | 06  | ッ   |     |
| 0x5D30h | 07  | ャ   |     |
| 0x5D38h | 08  | ュ   |     |
| 0x5D40h | 09  | ョ   |     |
| 0x5D48h | 0A  | ゃ   |     |
| 0x5D50h | 0B  | ゅ   |     |
| 0x5D58h | 0C  | ょ   |     |
| 0x5D60h | 0D  | っ   |     |
| 0x5D68h | 0E  | !   |     |
| 0x5D70h | 0F  | ?   |     |
| 0x5D78h | 10  | A   |     |
| 0x5D80h | 11  | C   |     |
| 0x5D88h | 12  | D   |     |
| 0x5D90h | 13  | E   |     |
| 0x5D98h | 14  | G   |     |
| 0x5DA0h | 15  | I   |     |
| 0x5DA8h | 16  | K   |     |
| 0x5DB0h | 17  | L   |     |
| 0x5DB8h | 18  | M   |     |
| 0x5DC0h | 19  | N   |     |
| 0x5DC8h | 1A  | O   |     |
| 0x5DD0h | 1B  | P   |     |
| 0x5DD8h | 1C  | S   |     |
| 0x5DE0h | 1D  | T   |     |
| 0x5DE8h | 1E  | X   |     |
| 0x5DF0h | 1F  | Y   |     |
| 0x5DF8h | 20  |     |     |
| 0x5E00h | 21  | ♂   | ♂   |
| 0x5E08h | 22  | ♃   | ♃   |
| 0x5E10h | 23  | ♄   | ♄   |
| 0x5E18h | 24  | ⛢   | ⛢   |
| 0x5E20h | 25  | ♇   | ♇   |
| 0x5E28h | 26  | ♆   | ♆   |
| 0x5E30h | 27  | ☿   | ☿   |
| 0x5E38h | 28  | ☉   | ☉   |
| 0x5E40h | 29  | ☾   | ☾   |
| 0x5E48h | 2A  | ♀   | ♀   |
| 0x5E50h | 2B  | ゆ   | ˚   |
| 0x5E58h | 2C  | よ   | ,   |
| 0x5E60h | 2D  |  ﾞ   | -   |
| 0x5E68h | 2E  |  ﾟ   | .   |
| 0x5E70h | 2F  | U   | #   |
| 0x5E78h | 30  | 0   | 0   |
| 0x5E80h | 31  | 1   | 1   |
| 0x5E88h | 32  | 2   | 2   |
| 0x5E90h | 33  | 3   | 3   |
| 0x5E98h | 34  | 4   | 4   |
| 0x5EA0h | 35  | 5   | 5   |
| 0x5EA8h | 36  | 6   | 6   |
| 0x5EB0h | 37  | 7   | 7   |
| 0x5EB8h | 38  | 8   | 8   |
| 0x5EC0h | 39  | 9   | 9   |
| 0x5EC8h | 3A  | ら   | '   |
| 0x5ED0h | 3B  | り   |     |
| 0x5ED8h | 3C  | る   |     |
| 0x5EE0h | 3D  | れ   |     |
| 0x5EE8h | 3E  | ろ   |     |
| 0x5EF0h | 3F  | を   |     |
| 0x5FF8h | 40  | ・   |     |
| 0x5F00h | 41  | ア   | A   |
| 0x5F08h | 42  | イ   | B   |
| 0x5F10h | 43  | ウ   | C   |
| 0x5F18h | 44  | エ   | D   |
| 0x5F20h | 45  | オ   | E   |
| 0x5F28h | 46  | カ   | F   |
| 0x5F30h | 47  | キ   | G   |
| 0x5F38h | 48  | ク   | H   |
| 0x5F40h | 49  | ケ   | I   |
| 0x5F48h | 4A  | コ   | J   |
| 0x5F50h | 4B  | サ   | K   |
| 0x5F58h | 4C  | シ   | L   |
| 0x5F60h | 4D  | ス   | M   |
| 0x5F68h | 4E  | セ   | N   |
| 0x5F70h | 4F  | ソ   | O   |
| 0x5F78h | 50  | タ   | P   |
| 0x5F80h | 51  | チ   | Q   |
| 0x5F88h | 52  | ツ   | R   |
| 0x5F90h | 53  | テ   | S   |
| 0x5F98h | 54  | ト   | T   |
| 0x5FA0h | 55  | ナ   | U   |
| 0x5FA8h | 56  | ニ   | V   |
| 0x5FB0h | 57  | ヌ   | W   |
| 0x5FB8h | 58  | ネ   | X   |
| 0x5FC0h | 59  | ノ   | Y   |
| 0x5FC8h | 5A  | ハ   | Z   |
| 0x5FD0h | 5B  | ヒ   |     |
| 0x5FD8h | 5C  | フ   |     |
| 0x5FE0h | 5D  | ヘ   |     |
| 0x5FE8h | 5E  | ホ   |     |
| 0x5FF0h | 5F  | マ   |     |
| 0x5FF8h | 60  | ミ   |     |
| 0x6000h | 61  | ム   | a   |
| 0x6008h | 62  | メ   | b   |
| 0x6010h | 63  | モ   | c   |
| 0x6018h | 64  | ヤ   | d   |
| 0x6020h | 65  | ユ   | e   |
| 0x6028h | 66  | ヨ   | f   |
| 0x6030h | 67  | ラ   | g   |
| 0x6038h | 68  | リ   | h   |
| 0x6040h | 69  | ル   | i   |
| 0x6048h | 6A  | レ   | j   |
| 0x6050h | 6B  | ロ   | k   |
| 0x6058h | 6C  | ワ   | l   |
| 0x6060h | 6D  | ン   | m   |
| 0x6068h | 6E  | わ   | n   |
| 0x6070h | 6F  | ん   | o   |
| 0x6078h | 70  | ー   | p   |
| 0x6080h | 71  | あ   | q   |
| 0x6088h | 72  | い   | r   |
| 0x6090h | 73  | う   | s   |
| 0x6098h | 74  | え   | t   |
| 0x60A0h | 75  | お   | u   |
| 0x60A8h | 76  | か   | v   |
| 0x60B0h | 77  | き   | w   |
| 0x60B8h | 78  | く   | x   |
| 0x60C0h | 79  | け   | y   |
| 0x60C8h | 7A  | こ   | z   |
| 0x60D0h | 7B  | さ   | à   |
| 0x60D8h | 7C  | し   | è   |
| 0x60E0h | 7D  | す   | ì   |
| 0x60E8h | 7E  | せ   | ò   |
| 0x60F0h | 7F  | そ   | ù   |
| 0x60F8h | 80  | た   | á   |
| 0x6100h | 81  | ち   | é   |
| 0x6108h | 82  | つ   | í   |
| 0x6110h | 83  | て   | ó   |
| 0x6118h | 84  | と   | ú   |
| 0x6120h | 85  | な   | ñ   |
| 0x6128h | 86  | に   |     |
| 0x6130h | 87  | ぬ   |     |
| 0x6138h | 88  | ね   |     |
| 0x6140h | 89  | の   |     |
| 0x6148h | 8A  | は   |     |
| 0x6150h | 8B  | ひ   |     |
| 0x6158h | 8C  | ふ   |     |
| 0x6160h | 8D  | へ   |     |
| 0x6168h | 8E  | ほ   |     |
| 0x6170h | 8F  | ま   |     |
| 0x6078h | 90  | み   |     |
| 0x6180h | 91  | む   |     |
| 0x6188h | 92  | め   |     |
| 0x6190h | 93  | も   |     |
| 0x6198h | 94  | や   |     |
| 0x61A0h | 95  | 〜   |     |

### Konami Logo (0x61A8h)

32x32 pixel, 1bpp, 2-Dimensional

### Main Menu (0x6228h)

32x8 pixel, 1bpp, 2-Dimensional:

- 0x6228h: Memo
- 0x6248h: Communication
- 0x6268h: Deck
- 0x6288h: Bag

### Communications Menu (0x62A8h)

32x8 pixel, 1bpp, 2-Dimensional:

- 0x62A8h: Receive
- 0x62C8h: Send
- 0x62E8h: Mystery
- 0x6308h: Exit

### Mail (0x6388h)

32x16 pixel, 1bpp, 2-Dimensional

### Good Luck (0x635Ch)

32x11 pixel, 1bpp, 2-Dimensional

### Title Graphic (0x63C8h)

32x16 pixel, 1bpp, 2-Dimensional

### Deck Buttons (0x654Ch)

32x6 pixel, 1bpp, 2-Dimensional

### Values (0x6430h)

8x12 pixel, 1bpp, 1-Dimensional

### Card Types (0x643Ch)

8x8 pixel, 1bpp, 1-Dimensional:

- 0x643Ch: Dragon
- 0x6444h: Spellcaster
- 0x644Ch: Zombie
- 0x6454h: Warrior
- 0x645Ch: Beast-Warrior
- 0x6464h: Beast
- 0x646Ch: Winged Beast
- 0x6474h: Fiend
- 0x647Ch: Fairy
- 0x6484h: Insect
- 0x648Ch: Dinosaur
- 0x6494h: Reptile
- 0x649Ch: Fish
- 0x64A4h: Sea Serpent
- 0x64ACh: Machine
- 0x64B4h: Thunder
- 0x64BCh: Aqua
- 0x64C4h: Pyro
- 0x64CCh: Rock
- 0x64D4h: Plant
- 0x64DCh: Magic
- 0x64E4h: Trap
- 0x64ECh: Ritual
- 0x64F4h: Equip












































