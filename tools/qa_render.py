#!/usr/bin/env python3
"""Exercise signed X and native OAM packing through the actual player draw.

Positions the player partly outside the viewport using RAM as a QA hook.
"""
from test_snes import Runner,ROOT
import json
from hardware_checks import check_obj_cache,check_bg_cache
r=Runner();r.logic(5);r.press('START');r.logic(10);r.press('START');r.logic(5);r.press('START')
for _ in range(3):r.press('B')
r.logic(450)
r.write('players',21,2,r.layout['x']);r.write('players',100,2,r.layout['y'])
# An intentional entrance glide is allowed to cross the viewport boundary.
# Normal directional movement is checked separately by qa_player_bounds.py.
r.write('players',129,1,r.layout['invuln']);r.write('players',80,1,r.layout['invuln']+1)
r.write('players',0,1,r.layout['shots']+9*r.layout['shot_size']+1)
r.logic(1)
for _ in range(100):
    if r.read('native_phase',1)==4:break
    r.run(1)
else:raise AssertionError('Draw did not reach VBlank')
a=r.addr('oamMemory')&0x1ffff;b=bytes(r.ram[a:a+544]);visible=[]
for i in range(128):
    p=i*4;pair=(b[512+i//4]>>(2*(i%4)))&3;x=b[p]+((pair&1)<<8)
    if x>=256:x-=512
    if b[p+1]<224:visible.append({'index':i,'x':x,'y':b[p+1],'large':bool(pair&2)})
assert any(-32<o['x']<0 and o['large'] for o in visible),('Partially visible 32px sprite lost signed X',visible,r.read('players',2,r.layout['x']))
assert len(visible)==1,'Unused OAM entries became visible'
r.capture('oam-left-edge')
r.write('players',144,2,r.layout['x']);r.write('players',32,2,r.layout['y'])
r.write('players',0,1,r.layout['invuln']+1)
r.write('dbg_warp',0x102);r.write('players',255,1,r.layout['invuln']);r.write('players',9,1,r.layout['lives']);r.logic(200)
obj=check_obj_cache(r);bg=check_bg_cache(r);r.capture('vram-section-02')
before=r.read('bg_partial_updates')
r.logic(200)
bg_scrolled=check_bg_cache(r)
assert r.read('bg_partial_updates')>before,'Incremental scenery update did not run'
result={'rom_sha256':r.rom_sha256,'qa_position_override':True,'qa_section_warp':True,'visible_oam':visible,
        'ppu_obj_tiles':obj,'ppu_scenery_tiles':bg,'ppu_scrolled_tiles':bg_scrolled,'passed':True}
(ROOT/'build/qa/render.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
