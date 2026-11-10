#!/usr/bin/env python3
"""Differential check of optimized ticks/actions against their shared C paths."""
from native_probe import Probe,symbols,enemy_call
from test_snes import ROOT
import random,json,hashlib
s=symbols();e=s['en_big']
functions=['native_enemy_update','native_enemy_update_slow','native_enemy_collide','native_enemy_collide_slow']
p=Probe([enemy_call(s[fn],big,e) for big in range(2) for fn in functions]);r=p.r
rng=random.Random(3030)
raw=(ROOT/'snes/sidearms_md_snes.sfc').read_bytes();motion_addr=s['en_mot']&0x3fffff
show_steps=[i for i in range(2462) if raw[motion_addr+i*6]]
regions=[('en_big',360),('en_small',640),('en_item',320),('players',r.layout['player_size']*2),('combined',1),('combined_hp',1),
         ('native_enemy_cont',1),('tccs_src/logic/enemies.asm_n_live',3),('enemy_spawned',2)]
def snapshot():
    return {name:bytes(r.ram[(r.addr(name)&0x1ffff):(r.addr(name)&0x1ffff)+n]) for name,n in regions}
for case in range(1000):
    big=rng.randrange(2);action=case>=500
    x=rng.randrange(-70,360);y=rng.randrange(-30,240);flags=rng.choice([0,4,32,36,64]);timer=rng.choice([0,1,2,20,200])
    dx=rng.randrange(-4,5);dy=rng.randrange(-4,5);scrollx=rng.randrange(4096);scrolly=rng.randrange(4096)
    sdx=rng.randrange(-1,2);sdy=rng.randrange(-1,2);frame=rng.randrange(256)
    target=rng.randrange(2);inv=rng.choice([0,0,1,255]);item=rng.choice([0,1,2,3,4,6,0x80,0x81,0x10,0x11]) if not big else 0
    motion=139
    if not action and case%2==0:flags=rng.choice((4,36));timer=1;motion=rng.choice(show_steps)
    outputs=[]
    for slow in range(2):
        p.restore(big*4+(2 if action else 0)+slow)
        a=r.addr('en_big')&0x1ffff;r.ram[a:a+40]=bytes(40)
        for off,val,n in [(0,1,1),(1,1 if big else 2,1),(2,flags if not action else 0,1),(3,1,1),
                          (4,100 if action else x&65535,2),(6,80 if action else y&65535,2),(8,dy&255,1),(9,dx&255,1),
                          (10,timer,1),(11,5,1),(12,960,2),(14,motion,2),(16,1,1),(17,item if action else 0,1),(34,65535,2)]:
            r.write('en_big',val,n,off)
        for off in range(18,22):r.write('en_big',16,1,off)
        r.write('level',scrollx,2,4);r.write('level',scrolly,2,6)
        r.write('en_scroll_dx',sdx&255,1);r.write('en_scroll_dy',sdy&255,1)
        r.write('frame',big if action else frame)
        r.write('native_live_shots',0)
        for pi in range(2):
            off=pi*r.layout['player_size'];state=int(action and pi==target)
            r.write('players',state,2,off);r.write('players',3,1,off+r.layout['lives'])
            r.write('players',100 if big else 92,2,off+4);r.write('players',80 if big else 72,2,off+6)
            r.write('players',inv,1,off+r.layout['invuln'])
            r.write('pl_alive',state,1,pi);r.write('pl_y',(80 if big else 72)+16,1,pi)
            r.write('pl_x2',((100 if big else 92)+96)//2,1,pi)
        p.run();outputs.append(snapshot())
    assert outputs[0]==outputs[1],(case,big,action,[k for k in outputs[0] if outputs[0][k]!=outputs[1][k]])
result={'cases':1000,'ticks':500,'contact_actions':500,'rom_sha256':hashlib.sha256((ROOT/'snes/sidearms_md_snes.sfc').read_bytes()).hexdigest(),'passed':True}
(ROOT/'build/qa/native-enemy.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
