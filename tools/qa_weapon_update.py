#!/usr/bin/env python3
"""Compare native linear slot traversal with the original C update loop."""
import hashlib,json,random
from native_probe import Probe,symbols,le
from test_snes import ROOT
s=symbols();codes=[]
for fn in ('native_weapon_linear','native_linear_slow'):
 b=bytes.fromhex('18 fb c2 30 08 e2 20 af 40 ff 7f 48 c2 20 f4')+le(s['players']>>16)+b'\xf4'+le(s['players']&65535)+b'\x22'+le(s[fn],3)+bytes.fromhex('3b 18 69 05 00 1b a9 5a a5 8f 08 ff 7f 28 db');codes.append(b)
for fn in ('weapon_select','native_weapon_select_slow'):
 codes.append(bytes.fromhex('18 fb c2 30 08 f4')+le(s['players']>>16)+b'\xf4'+le(s['players']&65535)+b'\x22'+le(s[fn],3)+bytes.fromhex('3b 18 69 04 00 1b a9 5a a5 8f 08 ff 7f 28 db'))
p=Probe(codes);r=p.r;rng=random.Random(9224)
for case in range(1200):
 state=bytearray(rng.randbytes(284));n=rng.randrange(10)
 for k in range(9):
  at=36+k*22;state[at:at+8]=le(rng.randrange(-100,400)&65535)+le(rng.randrange(-40,250)&65535)+le(rng.randrange(-8,9)&65535)+le(rng.randrange(-8,9)&65535);state[at+8]=rng.randrange(4)
 out=[]
 for slow in range(2):
  p.restore(slow);a=r.addr('players')&0x1ffff;r.ram[a:a+284]=state;r.ram[0x1ff40]=n;p.run();out.append(bytes(r.ram[a:a+284]))
 assert out[0]==out[1],(case,n)
for case in range(600):
 state=bytearray(284);state[2]=rng.randrange(2);state[15]=rng.randrange(6) if case%2 else 0
 for k in range(1,6):state[16+k]=rng.choice((0,0,1,2,3))
 state[30]=rng.randrange(2);state[236]=rng.randrange(256);req=rng.randrange(8);out=[]
 for slow in range(2):
  p.restore(2+slow);a=r.addr('players')&0x1ffff;r.ram[a:a+284]=state;r.write('pad_weapon_req',req,1,state[2]);p.run();out.append((bytes(r.ram[a:a+284]),r.read('pad_weapon_req',2)))
 assert out[0]==out[1],('select',case)
result={'rom_sha256':hashlib.sha256((ROOT/'snes/sidearms_md_snes.sfc').read_bytes()).hexdigest(),'cases':1200,'select_cases':600,'passed':True};(ROOT/'build/qa/weapon-update.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
