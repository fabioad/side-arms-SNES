#!/usr/bin/env python3
"""Check native slot iteration against individual calls in the same order."""
import hashlib,json,random
from native_probe import Probe,symbols,le
from test_snes import ROOT
s=symbols();codes=[];base=s['en_big'];prefix=bytes.fromhex('18 fb c2 30 08');end=bytes.fromhex('a9 5a a5 8f 08 ff 7f 28 db')
for big in range(2):
    args=bytes.fromhex('e2 20 a9')+bytes([big])+bytes.fromhex('48 c2 20 f4')+le(3)+b'\xf4'+le(base>>16)+b'\xf4'+le(base&65535)
    codes.append(prefix+args+b'\x22'+le(s['native_enemy_pool'],3)+bytes.fromhex('3b 18 69 07 00 1b')+end)
    b=prefix
    for k in range(3):
        ptr=base+k*40
        body=bytes.fromhex('e2 20 a9')+bytes([big])+bytes.fromhex('48 c2 20 f4')+le(ptr>>16)+b'\xf4'+le(ptr&65535)+b'\x22'+le(s['native_enemy_update'],3)+bytes.fromhex('3b 18 69 05 00 1b')
        b+=b'\xaf'+le(ptr,3)+bytes.fromhex('29 ff 00 f0')+bytes([len(body)])+body
    codes.append(b+end)
p=Probe(codes);r=p.r;rng=random.Random(3340)
regions=[('en_big',360),('en_small',640),('en_item',320),('players',568),('enemy_spawned',2),('tccs_src/logic/enemies.asm_n_live',3)]
for case in range(300):
    big=case&1;pool=bytearray(120)
    for k in range(3):
        at=k*40;pool[at]=rng.randrange(2);pool[at+1]=1;pool[at+2]=rng.choice((4,36));pool[at+3]=1
        pool[at+4:at+8]=le(rng.randrange(40,240))+le(rng.randrange(20,180));pool[at+8:at+10]=bytes((rng.randrange(5),rng.randrange(5)))
        pool[at+10]=rng.randrange(2,100);pool[at+12:at+14]=le(960);pool[at+34:at+36]=le(65535)
    out=[]
    for slow in range(2):
        p.restore(big*2+slow);a=base&0x1ffff;r.ram[a:a+120]=pool;r.write('native_live_shots',0);r.write('players',0);r.write('players',0,2,284);p.run()
        out.append({n:bytes(r.ram[(r.addr(n)&0x1ffff):(r.addr(n)&0x1ffff)+size]) for n,size in regions})
    assert out[0]==out[1],(case,[n for n in out[0] if out[0][n]!=out[1][n]])
result={'rom_sha256':hashlib.sha256((ROOT/'snes/sidearms_md_snes.sfc').read_bytes()).hexdigest(),'cases':300,'passed':True};(ROOT/'build/qa/enemy-pool.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
