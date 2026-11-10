#!/usr/bin/env python3
"""Ensure the complete Home subtitle survives BG1 map DMA and menu changes."""
import json,struct
from test_snes import Runner,ROOT
r=Runner();r.logic(5);r.press('DOWN');r.press('START');r.logic(10)
patterns=(ROOT/'snes/res/native_home_snes_tiles.bin').read_bytes()
cells=struct.unpack('<64H',(ROOT/'snes/res/native_home_snes_map.bin').read_bytes())
def check():
    assert r.read('flow_state')==9,'Home screen missing'
    v=r.snapshot_block(b'VRA')
    # BG1 uses $8000 bytes for characters and $B000..$B7FF for its map.
    # The previous subtitle at tile 341 crossed into that map at tile 384.
    assert len(patterns)<=2048
    assert v[0xb800:0xb800+len(patterns)]==patterns,'Home subtitle patterns overwritten in VRAM'
    for y in range(4):
        for x in range(16):
            e=cells[y*16+x]
            want=((e&2047)-1+448)|((2+(e>>13&1))<<10)|0x2000 if e else 0
            offset=0xb000+((11+y)*32+8+x)*2
            assert int.from_bytes(v[offset:offset+2],'little')==want,(x,y,'Home subtitle map mismatch')
    assert not r.read('native_dma_late') and not r.read('native_dma_overflow')
check()
for _ in range(6):r.press('DOWN');r.logic(3);check()
r.press('Y');r.logic(10);assert r.read('flow_state')==1
r.press('B');r.logic(10);check()
r.capture('home-snes-fixed')
result={'rom_sha256':r.rom_sha256,'complete_pattern_bytes':len(patterns),'initial_home':True,'cursor_changes':6,'options_return':True,'passed':True}
(ROOT/'build/qa/home-logo.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
