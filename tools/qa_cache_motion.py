#!/usr/bin/env python3
"""Independent LRU model and original motion-step field semantics."""
import hashlib,json,random,struct
from native_probe import Probe,symbols,le
from test_snes import ROOT
s=symbols();codes=[]
for fn in ('native_bg_slot','native_enemy_show'):
 b=bytes.fromhex('18 fb c2 30 08 af 40 ff 7f 48')
 if fn.endswith('show'):b+=b'\xf4'+le(s['en_big']>>16)+b'\xf4'+le(s['en_big']&65535)
 b+=b'\x22'+le(s[fn],3)+b'\xaf'+le(s['tcc__r0'],3)+bytes.fromhex('8f 00 ff 7f 3b 18 69')+le(6 if fn.endswith('show') else 2)+bytes.fromhex('1b a9 5a a5 8f 08 ff 7f 28 db');codes.append(b)
p=Probe(codes);r=p.r;rng=random.Random(47322462)
def put(name,b):
 a=r.addr(name)&0x1ffff;r.ram[a:a+len(b)]=b
def get(name,n):
 a=r.addr(name)&0x1ffff;return bytes(r.ram[a:a+n])
for case in range(1600):
 p.restore(0);stamp=rng.randrange(65536);misses=rng.randrange(65536);chosen=rng.sample(range(1024),47);keys=[v if rng.randrange(4) else 65535 for v in chosen];used=[rng.randrange(65536) for _ in keys]
 if case%7==0:used=[stamp]*47
 if case%11==0:keys[0]=chosen[0];used[0]=(stamp+1)&65535
 meta=rng.choice(chosen) if case%2 else rng.randrange(1024,1050) if case%13==0 else next(v for v in range(1024) if v not in keys)
 hint=bytearray(1024)
 for i,key in enumerate(keys):
  if key!=65535:hint[key]=i+1
 put('native_bg_keys',struct.pack('<47H',*keys));put('native_bg_used',struct.pack('<47H',*used));put('native_meta_slot',hint);r.write('native_bg_stamp',stamp);r.write('native_bg_misses',misses);r.ram[0x1ff40:0x1ff42]=le(meta)
 expected=65535
 if meta<1024:
  if hint[meta]:expected=hint[meta]-1;used[expected]=stamp
  else:
   age=0;slot=0
   for i,key in enumerate(keys):
    d=65535 if key==65535 else (stamp-used[i])&65535
    if d>age:age=d;slot=i
   if age:
    if keys[slot]!=65535:hint[keys[slot]]=0
    keys[slot]=meta;used[slot]=stamp;hint[meta]=slot+1;misses=(misses+1)&65535;expected=slot|32768
 p.run();actual=int.from_bytes(bytes(r.ram[0x1ff00:0x1ff02]),'little');assert actual==expected,(case,actual,expected)
 assert get('native_bg_keys',94)==struct.pack('<47H',*keys)
 assert get('native_bg_used',94)==struct.pack('<47H',*used)
 assert get('native_meta_slot',1024)==hint and r.read('native_bg_misses')==misses
rom=(ROOT/'snes/sidearms_md_snes.sfc').read_bytes();addr=s['en_mot']&0x3fffff;steps=rom[addr:addr+2462*6]
for case in range(1600):
 p.restore(1);idx=rng.randrange(2462);enemy=bytearray(rng.randbytes(40));cont=rng.randrange(256);expected=bytearray(enemy);result=0;out_cont=cont;at=idx
 for _ in range(32):
  st=steps[at*6:at*6+6]
  if st[0]:
   expected[12:14]=st[4:6];expected[8:10]=st[2:4];expected[10:12]=st[:2];expected[14:16]=le(at+1);out_cont=1;result=1;break
  if st[1]!=0:break
  at=int.from_bytes(st[4:6],'little')
 put('en_big',enemy);r.write('native_enemy_cont',cont,1);r.ram[0x1ff40:0x1ff42]=le(idx);p.run()
 assert r.ram[0x1ff00]==result and get('en_big',40)==expected and r.read('native_enemy_cont',1)==out_cont,(case,idx,'motion fields')
result={'rom_sha256':hashlib.sha256(rom).hexdigest(),'cache_cases':1600,'motion_cases':1600,'passed':True}
(ROOT/'build/qa/cache-motion.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
