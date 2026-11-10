#!/usr/bin/env python3
"""Hold both directions for P1/P2 and the combined robot in an isolated lane.

QA removes enemies and keeps entry protection latched to isolate directional
bounds from terrain and combat; it does not change the movement coordinates.
"""
from test_snes import Runner,ROOT
import json
r=Runner(False);r.logic(5);r.press('DOWN');r.press('START');r.logic(10);r.press('START');r.logic(20)
for _ in range(3):r.press('B')
r.logic(450);assert r.read('flow_state')==7
r.press('START',1)
for _ in range(3):r.press('B',1)
r.logic(75)
size=r.layout['player_size'];entry=r.layout['invuln']+1;latch=r.layout['shots']+9*r.layout['shot_size']+1
assert r.read('players',2)==1 and r.read('players',2,size)==1
r.write('en_dbg_mute',1,1)
for name,n in [('en_small',16),('en_big',9),('en_item',8)]:
    for i in range(n):r.write(name,0,1,i*40)
r.write('tccs_src/logic/enemies.asm_n_live',0,3);r.write('tccs_src/logic/enemies.asm_bullets_live',0,1)
def protect():
    for i in range(2):
        o=i*size;r.write('players',255,1,o+r.layout['invuln']);r.write('players',2,1,o+entry)
        r.write('players',1,1,o+latch);r.write('players',3,1,o+14)
for i in range(2):
    r.write('players',144,2,i*size+r.layout['x']);r.write('players',64+i*64,2,i*size+r.layout['y'])
rows=[]
def hold(port,button,label):
    r.masks=[0,0];positions=[]
    for _ in range(120):
        protect();r.logic(1,[button],port)
        x=r.read('players',2,port*size+r.layout['x']);positions.append(x)
        assert 32<=x<=256,(label,x)
    target=32 if button=='LEFT' else 256
    assert positions[-1]==target,(label,positions[-1],target)
    r.masks=[0,0]
    rows.append({'case':label,'logical_x':target,'visible_x':target-32,'body_right':target,'frames':120})
for port in range(2):
    hold(port,'LEFT',f'p{port+1}-left');hold(port,'RIGHT',f'p{port+1}-right')
r.write('players',144,2,r.layout['x']);r.write('players',16,2,r.layout['y']);r.write('dbg_player_cmd',6,1)
for _ in range(300):protect();r.logic(1)
assert r.read('combined',1)==1,'Robot transformation did not finish'
hold(0,'LEFT','robot-left');hold(0,'RIGHT','robot-right')
assert r.read('combined',1)==1
assert r.read('native_dma_overflow')==0 and r.read('native_dma_late')==0
result={'rom_sha256':r.rom_sha256,'qa_isolated_world':True,'qa_entry_protection':True,'cases':rows,'passed':True}
(ROOT/'build/qa/player-bounds.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
