#!/usr/bin/env python3
"""Compare native cache lookup/LRU with the original strict-age selection rule."""
from native_probe import Probe,symbols,le
from test_snes import ROOT
import random,json,hashlib
s=symbols();programs=[]
for fn in ('native_big_find','native_big_victim'):
    code=bytearray.fromhex('18 fb c2 30 08')
    if fn=='native_big_find':code+=b'\xaf'+le(0x7fff00,3)+b'\x48'
    code+=b'\x22'+le(s[fn],3)
    if fn=='native_big_find':code+=bytes.fromhex('c2 30 3b 18 69 02 00 1b')
    code+=b'\xaf'+le(s['tcc__r0'],3)+b'\x8f'+le(0x7fff04,3)
    code+=bytes.fromhex('a9 5a a5 8f 08 ff 7f 28 db');programs.append(code)
p=Probe(programs);r=p.r;rng=random.Random(1248)
for case in range(1200):
    stamp=rng.randrange(65536);keys=[rng.randrange(32768) for _ in range(12)];used=[rng.randrange(65536) for _ in range(12)]
    if case%4==0:used=[stamp]*12
    if case%4==1:keys[rng.randrange(12)]=65535
    if case%4==2:used[0]=(stamp+1)&65535;keys[4]=65535
    query=rng.choice(keys) if case%2 else rng.randrange(32768)
    victim=65535;age=0
    for i,key in enumerate(keys):
        d=65535 if key==65535 else (stamp-used[i])&65535
        if d>age:victim=i;age=d
    expected=[keys.index(query) if query in keys else 65535,victim]
    for fn in range(2):
        p.restore(fn);r.ram[0x1ff00:0x1ff02]=le(query);r.write('native_spr_stamp',stamp)
        for i in range(12):r.write('native_big_keys',keys[i],2,i*2);r.write('native_big_used',used[i],2,i*2)
        p.run();actual=int.from_bytes(bytes(r.ram[0x1ff04:0x1ff06]),'little')
        assert actual==expected[fn],(case,fn,actual,expected[fn])
result={'cases':1200,'rom_sha256':hashlib.sha256((ROOT/'snes/sidearms_md_snes.sfc').read_bytes()).hexdigest(),'passed':True}
(ROOT/'build/qa/native-cache.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
