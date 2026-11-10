#!/usr/bin/env python3
"""Compare metatile expansion with the independent former 16-cell algorithm."""
import random,json,hashlib
from native_probe import Probe,symbols,le
from test_snes import ROOT
s=symbols();b=bytes.fromhex('18 fb c2 30 08')
for off in (8,6,4,2,0):b+=b'\xaf'+le(0x7fff40+off,3)+b'\x48'
b+=b'\x22'+le(s['native_bg_cell'],3)+bytes.fromhex('3b 18 69 0a 00 1b a9 5a a5 8f 08 ff 7f 28 db')
p=Probe([b]);r=p.r;rng=random.Random(163032)
for case in range(1000):
 p.restore(0);slot=rng.randrange(47);e=rng.randrange(65536);index=rng.randrange(2)*1024+rng.randrange(8)*128+rng.randrange(8)*4;null=case%11==0
 tmpl=[rng.choice([0,0,0x2000,0x8000,0xa000,0x3fff]) for _ in range(16)];ptr=0 if null else 0x7fff80
 r.ram[0x1ff40:0x1ff4a]=le(ptr&65535)+le(ptr>>16)+le(slot)+le(e)+le(index);r.ram[0x1ff80:0x1ffa0]=b''.join(le(v) for v in tmpl)
 expected=bytearray(b'\x34\x12'*2048);a=r.addr('native_bg_map')&0x1ffff;r.ram[a:a+4096]=expected
 for y in range(4):
  for x in range(4):
   t=(3-y if e&0x8000 else y)*4+(3-x if e&0x4000 else x);attr=0 if null else tmpl[t]
   v=16+slot*16+t+(((attr>>13)&1)<<10)+0x3000+(e&0xc000) if attr else 0
   pos=(index+y*32+x)*2;expected[pos:pos+2]=le(v)
 p.run();assert bytes(r.ram[a:a+4096])==expected,(case,slot,e,index)
result={'rom_sha256':hashlib.sha256((ROOT/'snes/sidearms_md_snes.sfc').read_bytes()).hexdigest(),'cases':1000,'passed':True}
(ROOT/'build/qa/bg-native.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
