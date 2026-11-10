#!/usr/bin/env python3
"""Compare optimized enemy/weapon draw groups with their C paths and OAM order."""
import hashlib,json,random
from native_probe import Probe,symbols,le
from test_snes import ROOT
s=symbols();programs=[]
functions=(('native_enemy_draw_small','native_enemy_draw_small_slow'),('native_enemy_draw_big','native_enemy_draw_big_slow'),('weapons_draw','native_weapons_draw_slow'))
for kind,pair in enumerate(functions):
 for fn in pair:
  b=bytes.fromhex('18 fb c2 30 08');offsets=(6,4,2,0) if kind==0 else (0,) if kind==1 else (2,0)
  for off in offsets:b+=b'\xaf'+le(0x7fff40+off,3)+b'\x48'
  b+=b'\x22'+le(s[fn],3)+bytes.fromhex('c2 30 3b 18 69')+le(len(offsets)*2)+bytes.fromhex('1b a9 5a a5 8f 08 ff 7f 28 db');programs.append(b)
p=Probe(programs);r=p.r;rng=random.Random(164016)
for case in range(900):
 kind=case%3;n=rng.choice((0,8,16));rot=rng.randrange(n) if n else 0;index=rng.randrange(9);pi=rng.randrange(2);state=rng.randrange(3)
 enemies=bytearray(640)
 for i in range(16):
  off=i*40;enemies[off]=rng.randrange(2);enemies[off+4:off+8]=le(rng.randrange(-40,340)&65535)+le(rng.randrange(-40,250)&65535);enemies[off+11]=5;enemies[off+12:off+14]=le(960+rng.randrange(4) if rng.randrange(5) else 0)
 shots=bytearray(198)
 for i in range(9):
  off=i*22;shots[off:off+4]=le(rng.randrange(-40,340)&65535)+le(rng.randrange(-40,250)&65535);shots[off+8]=rng.randrange(3);shots[off+16:off+19]=le(960+rng.randrange(4))+bytes([5])
 outputs=[]
 for slow in range(2):
  p.restore(kind*2+slow);r.write('native_spr_count',0);r.write('native_spr_stamp',10)
  o=r.addr('oamMemory')&0x1ffff;r.ram[o:o+544]=bytes(544)
  for j in range(4):
   code=960+j;key=code|(5<<11)
   r.write('native_big_keys',key,2,j*2);r.write('native_big_hint',j+1,1,code);r.write('native_big_attributes',192+j*4|0x3000,2,j*2)
   r.write('tccs_src/sprites.asm_keys',key,2,j*2);r.write('native_sprite_hint',j+1,1,key);r.write('native_small_attributes',j*2|0x3000,2,j*2)
  for pool,size in (('en_small',640),('en_big',360)):
   a=r.addr(pool)&0x1ffff;r.ram[a:a+size]=enemies[:size]
  a=(r.addr('players')&0x1ffff)+pi*284;r.ram[a:a+284]=bytes(284);r.ram[a:a+2]=le(state);r.ram[a+36:a+234]=shots
  arg=le(s['en_small']&65535)+le(s['en_small']>>16)+le(n)+le(rot) if kind==0 else le(index) if kind==1 else le((s['players']+pi*284)&65535)+le((s['players']+pi*284)>>16)
  r.ram[0x1ff40:0x1ff40+len(arg)]=arg;p.run();outputs.append((bytes(r.ram[o:o+544]),r.read('native_spr_count')))
 assert outputs[0]==outputs[1],(case,kind,n,rot,'OAM differs')
result={'rom_sha256':hashlib.sha256((ROOT/'snes/sidearms_md_snes.sfc').read_bytes()).hexdigest(),'cases':900,'passed':True}
(ROOT/'build/qa/draw-groups.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
