#!/usr/bin/env python3
"""Home-mode entry, SRAM reset persistence, joining P2 and pad mapping."""
import ctypes as C,json
from test_snes import Runner,ROOT
from hardware_checks import check_obj_cache
r=Runner();r.logic(5);r.press('DOWN');r.press('START');r.logic(10)
assert r.read('flow_state')==9,'Home menu did not open'
r.core.retro_get_memory_size.argtypes=[C.c_uint];r.core.retro_get_memory_size.restype=C.c_size_t
size=r.core.retro_get_memory_size(0);ptr=r.core.retro_get_memory_data(0)
assert size==8192 and ptr,'Battery SRAM missing'
saved=C.string_at(ptr,size)
assert saved[:4]==b'SAR2','Settings not written to battery SRAM'
r.capture('home');r.core.retro_reset();r.run(500)
assert r.read('game_cfg',1)==1,'Home mode setting did not survive reset'
r.logic(5);r.press('START');r.logic(5)
assert r.read('flow_state')==9,'Saved Home selection not restored'
r.press('START');r.logic(20) # wait for Home's intro scene set before confirming letters
for _ in range(3):r.press('B')
goal=r.read('frame_counter',4)+900
while r.read('frame_counter',4)<goal:
    r.write('players',255,1,r.layout['invuln']);r.run(1)
    if r.read('flow_state')==7 and r.read('players',2)==1:break
print('Home start:',r.read('flow_state'),'frames',r.read('frame_counter',4),flush=True)
print('players before join',r.read('players',2),r.read('players',2,r.layout['player_size']),
      'lives',r.read('players',1,r.layout['lives']),r.read('players',1,r.layout['player_size']+r.layout['lives']),flush=True)
r.capture('home-start')
assert r.read('flow_state')==7,'Home start did not reach gameplay'
assert r.read('players',2)==1,'Player 1 did not spawn'
r.write('players',255,1,r.layout['invuln'])
r.press('START',1)
for _ in range(3):r.press('B',1)
r.logic(75)
p2=r.layout['player_size']
assert r.read('players',2,p2)==1,'Player 2 did not spawn'
r.write('players',255,1,p2+r.layout['invuln']);r.write('players',255,1,r.layout['invuln'])
r.write('players',0,1,p2+r.layout['invuln']+1) # end the entry glide for the directional test
r.write('players',100,2,p2+r.layout['x']);r.write('players',32,2,p2+r.layout['y'])
before=r.read('players',2,p2+r.layout['x'])
r.logic(20,['RIGHT'],1)
assert r.read('pad',1,2)&1,'Player 2 direction did not reach the logical pad'
after=r.read('players',2,p2+r.layout['x'])
assert after>=before,'Player 2 moved against the requested direction'
r.write('players',129,1,p2+r.layout['invuln']);r.write('players',129,1,r.layout['invuln']);r.logic(1)
assert r.read('players',2)==1 and r.read('players',2,p2)==1,'Both players must be alive'
r.capture('two-players')
obj_check=check_obj_cache(r)
result={'rom_sha256':r.rom_sha256,'sram_bytes':size,'magic':saved[:4].decode(),'home_setting_survived_reset':True,
        'player1_state':r.read('players',2),'player2_state':r.read('players',2,p2),'player2_x_before':before,'player2_x_after':after,
        'dma_overflow':r.read('native_dma_overflow'),'audio_peak':r.audio_peak,'audio_timeouts':r.read('audio_flush_timeouts'),
        'ppu_obj_tiles':obj_check}
(ROOT/'build/qa/frontend.json').write_text(json.dumps(result,indent=2)+'\n')
(ROOT/'build/qa/save.srm').write_bytes(C.string_at(ptr,size))
assert result['dma_overflow']==0
assert result['audio_timeouts']==0
print(result)
