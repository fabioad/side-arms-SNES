#!/usr/bin/env python3
"""Exercise Home option edits, control remapping, Sound Test and SRAM reset."""
from test_snes import Runner,ROOT
import json
r=Runner();r.logic(5);r.press('DOWN');r.press('START');r.logic(5)
for _ in range(2):r.press('DOWN')
r.press('Y');assert r.read('flow_state')==1,'Options did not open'
r.press('RIGHT');r.press('DOWN');r.press('RIGHT') # difficulty and lives
for _ in range(4):r.press('DOWN')
r.press('RIGHT');assert r.read('color_mode',1)==0,'Arcade palette preview did not apply'
r.press('DOWN');r.press('RIGHT') # save PARALLAX OFF
r.press('DOWN');r.press('Y');assert r.read('flow_state')==10,'Controls did not open'
r.press('RIGHT');assert r.read('pad_cfg',1)==1,'Fire-left remapping failed'
r.press('B');assert r.read('flow_state')==1
r.press('DOWN');r.press('Y');assert r.read('flow_state')==11,'Sound Test did not open'
r.press('Y');r.logic(5);assert r.read('audio_last_command',1)==0x20
r.press('RIGHT');r.press('Y');r.logic(5);assert r.read('audio_last_command',1)==0x21
r.press('DOWN');r.press('Y');r.press('DOWN');r.press('Y') # effect then stop
r.logic(5)
vram=r.snapshot_block(b'VRA')
a=r.addr('hud_map')&0x1ffff
assert vram[0xb000:0xb000+28*64]==bytes(r.ram[a:a+28*64]),'HUD map DMA missed VBlank'
font=(ROOT/'snes/res/snes_font_tiles.bin').read_bytes()
for i in range(r.read('glyph_count')):
    key=r.read('glyph_keys',2,i*2);tile=r.read('glyph_entries',2,i*2)&1023
    code=key&1023;colour=key>>10
    if code<256:
        offset=(colour*256+code)*32
        assert vram[0x8000+tile*32:0x8000+(tile+1)*32]==font[offset:offset+32],f'Font DMA corrupted glyph {i}'
r.capture('sound-test');r.press('B');r.press('B');assert r.read('flow_state')==9
values={'difficulty':r.read('home_cfg',1),'lives':r.read('home_cfg',1,1),
        'parallax_setting':r.read('home_cfg',1,5),'fire_left_button':r.read('pad_cfg',1),'color':r.read('color_mode',1)}
assert values=={'difficulty':4,'lives':4,'parallax_setting':0,'fire_left_button':1,'color':0},values
r.core.retro_reset();r.run(500)
assert r.read('home_cfg',1)==4 and r.read('home_cfg',1,1)==4
assert r.read('home_cfg',1,5)==0 and r.read('pad_cfg',1)==1 and r.read('color_mode',1)==0
assert r.read('audio_flush_timeouts')==0
result={'rom_sha256':r.rom_sha256,'settings':values,'survived_reset':True,'sound_test_played':[0x20,0x21],
        'ppu_hud_map_matches_shadow':True,'ppu_font_tiles_match_rom':True,'passed':True}
(ROOT/'build/qa/options.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
