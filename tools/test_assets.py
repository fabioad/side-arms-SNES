#!/usr/bin/env python3
"""Validate actual cartridge bytes, tile planes and cross-bank asset continuity."""
from pathlib import Path
import re,sys
from prepare_snes import planar
ROOT=Path(__file__).resolve().parents[1]
rom=(ROOT/'snes/sidearms_md_snes.sfc').read_bytes()
symbols={}
for line in (ROOT/'snes/sidearms_md_snes.sym').read_text().splitlines():
    m=re.match(r'^([0-9a-fA-F]+) (\S+)$',line)
    if m:symbols[m[2]]=int(m[1],16)
def check(name,data):
    a=symbols[name];off=((a>>16)&63)*65536+(a&65535)
    assert rom[off:off+len(data)]==data, f'{name}: cartridge data mismatch at {off:x}'
count=0
for file in (ROOT/'snes/res').glob('*.bin'):
    if file.stem in symbols:check(file.stem,file.read_bytes());count+=1
check('SOUNDBANK__0',(ROOT/'snes/res/soundbank.bnk').read_bytes())
assert len(rom)==4*1024*1024
assert int.from_bytes(rom[0xffdc:0xffde],'little') ^ int.from_bytes(rom[0xffde:0xffe0],'little')==65535
assert sum(rom)&65535==int.from_bytes(rom[0xffde:0xffe0],'little')
# An independent inverse decoder checks every source tile pixel.
raw=(ROOT/'res/generated/sprite_pens.bin').read_bytes()[:128]
encoded=planar(raw)
for tile in range(4):
    for y in range(8):
        for x in range(8):
            pen=sum(((encoded[tile*32+(p//2)*16+y*2+(p&1)]>>(7-x))&1)<<p for p in range(4))
            expected=(raw[tile*32+y*4+x//2]>>(0 if x&1 else 4))&15
            assert pen==expected
print(f'PASS: {count} complete graphics/data blobs, sound banks, tile planes and SNES checksum')
