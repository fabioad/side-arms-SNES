#!/usr/bin/env python3
"""Compare cached native sprite submission with the C reference, including OAM."""
from native_probe import Probe,symbols,le
from test_snes import ROOT
import random,json,hashlib
s=symbols();programs=[]
for fn in ('spr_16','spr_16_slow','spr_32','spr_32_slow'):
    code=bytearray.fromhex('18 fb c2 30 08 e2 20')
    code+=b'\xaf'+le(0x7fff47,3)+bytes.fromhex('48 c2 30')
    for addr in (0x7fff45,0x7fff43):code+=b'\xaf'+le(addr,3)+b'\x48'
    code+=bytes.fromhex('e2 20')+b'\xaf'+le(0x7fff42,3)+bytes.fromhex('48 c2 30')
    code+=b'\xaf'+le(0x7fff40,3)+b'\x48\x22'+le(s[fn],3)
    code+=bytes.fromhex('c2 30 3b 18 69 08 00 1b a9 5a a5 8f 08 ff 7f 28 db');programs.append(code)
p=Probe(programs);r=p.r;rng=random.Random(161632);emitted=0
for case in range(1200):
    big=rng.randrange(2);slot=rng.randrange(12 if big else 48);code=rng.randrange(2048);col=rng.randrange(16)
    flags=rng.randrange(4);x=rng.randrange(-60,330);y=rng.randrange(-40,250);count=rng.choice([0,1,3,60,127,128])
    stamp=rng.randrange(65536);pal=rng.randrange(2);key=code|(col<<11)
    tile=192+(slot//4)*64+(slot%4)*4 if big else ((slot&0x38)<<2)|((slot&7)<<1)
    attr=tile|(pal<<9)|0x3000;outputs=[]
    for slow in range(2):
        p.restore(big*2+slow)
        r.ram[0x1ff40:0x1ff48]=le(code)+bytes([col])+le(x&65535)+le(y&65535)+bytes([flags])
        r.write('native_spr_count',count);r.write('native_spr_stamp',stamp);r.write('spr_dbg_dropped',0,4)
        a=r.addr('oamMemory')&0x1ffff;r.ram[a:a+544]=bytes(544)
        if big:
            r.write('native_big_keys',key,2,slot*2);r.write('native_big_hint',slot+1,1,code)
            used='native_big_used';attributes='native_big_attributes'
        else:
            r.write('tccs_src/sprites.asm_keys',key,2,slot*2);r.write('native_sprite_hint',slot+1,1,key)
            used='native_small_used';attributes='native_small_attributes'
        r.write(attributes,attr,2,slot*2);r.write(used,0,2,slot*2)
        p.run();outputs.append((bytes(r.ram[a:a+544]),r.read('native_spr_count'),r.read('spr_dbg_dropped',4),r.read(used,2,slot*2)))
    assert outputs[0]==outputs[1],(case,big,x,y,flags,count)
    emitted+=outputs[0][1]>count
assert emitted>200
result={'cases':1200,'emitted':emitted,'rom_sha256':hashlib.sha256((ROOT/'snes/sidearms_md_snes.sfc').read_bytes()).hexdigest(),'passed':True}
(ROOT/'build/qa/native-sprites.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
