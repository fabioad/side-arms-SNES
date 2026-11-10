#!/usr/bin/env python3
"""Differential checks for boss contact and projectile rendering."""
import hashlib,json,random
from native_probe import Probe,symbols,le
from test_snes import ROOT
s=symbols();rng=random.Random(30030);codes=[]
for fn in ('boss_touch','native_boss_touch_slow'):
 b=bytes.fromhex('18 fb c2 30 08')
 for off,n in ((7,1),(6,1),(5,1),(4,1),(2,2),(0,2)):
  if n==1:b+=bytes.fromhex('e2 20')
  b+=b'\xaf'+le(0x7fff40+off,3)+b'\x48'
  if n==1:b+=bytes.fromhex('c2 20')
 b+=b'\x22'+le(s[fn],3)+b'\xaf'+le(s['tcc__r0'],3)+bytes.fromhex('8f 04 ff 7f 3b 18 69 08 00 1b a9 5a a5 8f 08 ff 7f 28 db');codes.append(b)
for fn in ('pj_draw','native_pj_draw_slow'):
 codes.append(bytes.fromhex('18 fb c2 30 08')+b'\x22'+le(s[fn],3)+bytes.fromhex('a9 5a a5 8f 08 ff 7f 28 db'))
p=Probe(codes);r=p.r
for case in range(1000):
 py=rng.randrange(0,256);px=rng.randrange(40,450);hh=rng.randrange(1,70);hw=rng.randrange(1,70);oy=rng.randrange(-16,17);ox=rng.randrange(-16,17);shift=rng.randrange(-30,31)
 players=bytearray(568);expected=False
 for pi in range(2):
  off=284*pi;state=rng.choice((0,1,1,2));inv=rng.choice((0,0,1,255));y=py-16+rng.randrange(-80,81);x=px-96-shift+rng.randrange(-80,81)
  players[off:off+2]=le(state);players[off+2]=pi;players[off+4:off+8]=le(x&65535)+le(y&65535);players[off+22]=3;players[off+23]=inv
  expected|=state==1 and inv==0 and abs(y+16+oy-py)<hh and abs(x+96+shift+ox-px)<hw
 outputs=[]
 for slow in range(2):
  p.restore(slow);a=r.addr('players')&0x1ffff;r.ram[a:a+568]=players;r.write('boss_shift',shift&65535)
  r.ram[0x1ff40:0x1ff48]=le(py)+le(px)+bytes((hh,hw,oy&255,ox&255));p.run()
  assert bool(r.ram[0x1ff04])==expected,(case,slow,'contact result')
  outputs.append(bytes(r.ram[a:a+568]))
 assert outputs[0]==outputs[1],(case,'contact side effects')
for case in range(500):
 block=bytearray(1280);shift=rng.randrange(-20,21)
 for k in range(40):
  at=k*32;kind=rng.randrange(6);code=960+rng.randrange(4);x=rng.randrange(0,500);y=rng.randrange(-40,280)
  block[at]=kind;block[at+2:at+6]=le(y&65535)+le(x);block[at+20:at+23]=le(code)+bytes([5])
 outputs=[]
 for slow in range(2):
  p.restore(2+slow);a=r.addr('native_pj')&0x1ffff;r.ram[a:a+1280]=block;r.write('native_pj_live',sum(bool(block[k*32]) for k in range(40)));r.write('boss_shift',shift&65535)
  r.write('native_spr_count',0);r.write('native_spr_stamp',10)
  o=r.addr('oamMemory')&0x1ffff;r.ram[o:o+544]=bytes(544)
  for j in range(4):
   code=960+j;key=code|(5<<11)
   r.write('native_big_keys',key,2,j*2);r.write('native_big_hint',j+1,1,code);r.write('native_big_attributes',192+j*4|0x3000,2,j*2)
   r.write('tccs_src/sprites.asm_keys',key,2,j*2);r.write('native_sprite_hint',j+1,1,key);r.write('native_small_attributes',j*2|0x3000,2,j*2)
  p.run();outputs.append((bytes(r.ram[o:o+544]),r.read('native_spr_count')))
 assert outputs[0]==outputs[1],(case,'projectile OAM differs')
result={'rom_sha256':hashlib.sha256((ROOT/'snes/sidearms_md_snes.sfc').read_bytes()).hexdigest(),'contact_cases':1000,'projectile_draw_cases':500,'passed':True}
(ROOT/'build/qa/boss-native.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
