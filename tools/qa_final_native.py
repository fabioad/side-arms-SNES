#!/usr/bin/env python3
"""Compare the final boss's native field updates with their original C paths."""
import hashlib,json,random
from native_probe import Probe,symbols,le
from test_snes import ROOT
s=symbols();programs=[]
for fn in ('native_final_load','native_final_load_slow','native_final_move','native_final_move_slow'):
 programs.append(bytes.fromhex('18 fb c2 30 08')+b'\xf4'+le(0x7f)+b'\xf4'+le(0xfe00)+b'\x22'+le(s[fn],3)+bytes.fromhex('3b 18 69 04 00 1b a9 5a a5 8f 08 ff 7f 28 db'))
for fn in ('fboss_draw','native_final_draw_slow'):
 programs.append(bytes.fromhex('18 fb c2 30 08')+b'\x22'+le(s[fn],3)+bytes.fromhex('a9 5a a5 8f 08 ff 7f 28 db'))
p=Probe(programs);r=p.r;rng=random.Random(281628)
for case in range(1000):
 load=case%2==0;state=bytearray(rng.randbytes(28));state[9]=rng.randrange(8);state[12:16]=le(0xfe80)+le(0x7f);steps=rng.randbytes(48);outputs=[]
 for slow in range(2):
  p.restore((0 if load else 2)+slow);r.ram[0x1fe00:0x1fe1c]=state;r.ram[0x1fe80:0x1feb0]=steps;p.run();outputs.append(bytes(r.ram[0x1fe00:0x1fe1c]))
 assert outputs[0]==outputs[1],(case,load,outputs)
for case in range(500):
 state=bytearray(224);shift=rng.randrange(-20,21)
 for k in range(8):
  at=k*28;state[at]=rng.choice((0,1,0x48,0x4d,0x54));state[at+2:at+6]=le(rng.randrange(-40,280)&65535)+le(rng.randrange(0,500));state[at+16:at+19]=le(960+rng.randrange(4))+bytes([5])
 outputs=[]
 for slow in range(2):
  p.restore(4+slow);a=r.addr('tccs_src/logic/boss_final.asm_f')&0x1ffff;r.ram[a]=1;r.ram[a+2:a+226]=state;r.write('boss_shift',shift&65535);r.write('native_spr_count',0)
  o=r.addr('oamMemory')&0x1ffff;r.ram[o:o+544]=bytes(544)
  for j in range(4):
   code=960+j;r.write('native_big_keys',code|(5<<11),2,j*2);r.write('native_big_hint',j+1,1,code);r.write('native_big_attributes',192+j*4|0x3000,2,j*2)
  p.run();outputs.append((bytes(r.ram[o:o+544]),r.read('native_spr_count')))
 assert outputs[0]==outputs[1],('draw',case)
result={'rom_sha256':hashlib.sha256((ROOT/'snes/sidearms_md_snes.sfc').read_bytes()).hexdigest(),'cases':1000,'draw_cases':500,'passed':True}
(ROOT/'build/qa/final-native.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
