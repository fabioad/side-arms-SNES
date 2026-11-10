#!/usr/bin/env python3
"""Build the Capcom splash assets from the Street Fighter II (USA) capture.

The capture (tools/capcom_splash.png, frame 360 of the SF2 boot) is the exact
256x224 Snes9x output.  The logo occupies a 12x3-tile box at (80, 96); convert
that box to 4bpp SNES tiles plus one 16-colour palette per animation frame.
"""
from pathlib import Path
from PIL import Image
import struct

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'tools/capcom_splash.png'
DEST = ROOT / 'snes'
COLS, ROWS = 12, 3
X0, Y0 = 80, 96


def planar(packed):
    """8x8 packed nibbles (two pixels per byte) -> SNES 4bpp planar tile."""
    rows = [[0, 0, 0, 0] for _ in range(8)]
    for y in range(8):
        for x in range(8):
            pen = (packed[y * 4 + x // 2] >> (0 if x & 1 else 4)) & 15
            for p in range(4):
                rows[y][p] |= ((pen >> p) & 1) << (7 - x)
    out = bytearray()
    for a, b in ((0, 1), (2, 3)):
        for y in range(8):
            out.extend((rows[y][a], rows[y][b]))
    return bytes(out)


def gen_word(rgb, scale):
    """RGB -> Genesis colour word 0BBB0GGG0RRR0 (palette.c converts it)."""
    r, g, b = (min(7, max(0, round((v / 255.0) * 7.0 * scale))) for v in rgb)
    return (b << 9) | (g << 5) | (r << 1)


def main():
    img = Image.open(SRC).convert('RGB').crop((X0, Y0, X0 + COLS * 8, Y0 + ROWS * 8))
    counts = {}
    for y in range(ROWS * 8):
        for x in range(COLS * 8):
            c = img.getpixel((x, y))
            counts[c] = counts.get(c, 0) + 1
    # Colour 0 is the SNES transparent pen; keep it black.  The arcade logo
    # uses 15 flat colours, so the 16-entry palette is lossless.
    colors = sorted(counts, key=lambda c: (c != (0, 0, 0), -counts[c]))
    assert len(colors) <= 16, (len(colors), colors)
    lut = {c: i for i, c in enumerate(colors)}

    tiles = bytearray()
    for ty in range(ROWS):
        for tx in range(COLS):
            packed = bytearray()
            for y in range(8):
                for x in range(0, 8, 2):
                    a = lut[img.getpixel((tx * 8 + x, ty * 8 + y))]
                    b = lut[img.getpixel((tx * 8 + x + 1, ty * 8 + y))]
                    packed.append((a << 4) | b)
            tiles.extend(planar(packed))

    # image() in hud.c: 0 = blank, low 11 bits = tile + 1, bit 13 = PAL3.
    cmap = struct.pack('<' + str(COLS * ROWS) + 'H',
                       *((i + 1) | 0x2000 for i in range(COLS * ROWS)))
    # 60 fps palette animation: 56 frames of music lead-in, 60-frame fade in,
    # 90-frame hold, 60-frame fade out (266 frames total).
    frames = 266
    scales = []
    for f in range(frames):
        if f < 56:
            scales.append(0.0)
        elif f < 116:
            scales.append((f - 55) / 60.0)
        elif f < 206:
            scales.append(1.0)
        else:
            scales.append((frames - f) / 60.0)
    pal = bytearray()
    for scale in scales:
        for i in range(16):
            c = colors[i] if i < len(colors) else (0, 0, 0)
            pal += struct.pack('<H', gen_word(c, scale))

    DEST.joinpath('res').mkdir(parents=True, exist_ok=True)
    (DEST / 'res/fe_capcom_tiles.bin').write_bytes(tiles)
    (DEST / 'res/fe_capcom_map.bin').write_bytes(cmap)
    (DEST / 'res/fe_capcom_pal.bin').write_bytes(pal)

    asm = '''.INCLUDE "hdr.asm"
.BANK 5 SLOT 0
.ORG $0000
.SECTION "asset_fe_capcom_tiles_0" FORCE KEEP
fe_capcom_tiles:
.INCBIN "res/fe_capcom_tiles.bin"
.ENDS
.BANK 5 SLOT 0
.ORG $0500
.SECTION "asset_fe_capcom_map_0" FORCE KEEP
fe_capcom_map:
.INCBIN "res/fe_capcom_map.bin"
.ENDS
.BANK 5 SLOT 0
.ORG $0600
.SECTION "asset_fe_capcom_pal_0" FORCE KEEP
fe_capcom_pal:
.INCBIN "res/fe_capcom_pal.bin"
.ENDS
'''
    (DEST / 'src/capcom_assets.asm').write_text(asm)
    print(f'Capcom splash: {len(colors)} colours, {COLS * ROWS} tiles, {frames} palettes')


if __name__ == '__main__':
    main()
