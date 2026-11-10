#!/usr/bin/env python3
"""Compare projectile motion/counts with C and check contact eligibility."""
import hashlib,json,random
from native_probe import Probe,symbols,le
from test_snes import ROOT
s=symbols();codes=[]
for fn in ('native_pj_bullet_step','native_pj_bullet_step_slow','pj_bank_live','native_pj_bank_slow','pj_capped_live','native_pj_capped_slow','native_boss_contact_snapshot'):
    b=bytes.fromhex('18 fb c2 30 08');cleanup=0
    if 'bullet_step' in fn:
        b+=b'\xaf'+le(0x7fff40,3)+b'\x48\xf4'+le(0x7f)+b'\xf4'+le(0xfe00);cleanup=6
    elif fn in ('pj_bank_live','native_pj_bank_slow'):
        b+=bytes.fromhex('e2 20 af 40 ff 7f 48 c2 20');cleanup=1
    b+=b'\x22'+le(s[fn],3)+b'\xaf'+le(s['tcc__r0'],3)+bytes.fromhex('8f 00 ff 7f')
    if cleanup:b+=bytes.fromhex('3b 18 69')+le(cleanup)+b'\x1b'
    b+=bytes.fromhex('a9 5a a5 8f 08 ff 7f 28 db');codes.append(b)
p=Probe(codes);r=p.r;rng=random.Random(403230)
for case in range(800):
    state=bytearray(rng.randbytes(32));state[24]=rng.randrange(32);state[25]=rng.randrange(4);lvl=rng.randrange(4);out=[]
    for slow in range(2):
        p.restore(slow);r.ram[0x1fe00:0x1fe20]=state;r.ram[0x1ff40:0x1ff42]=le(lvl);p.run();out.append(bytes(r.ram[0x1fe00:0x1fe20]))
    assert out[0]==out[1],('bullet',case,out)
for case in range(400):
    pool=bytearray(rng.randbytes(1280));bank=rng.randrange(8)
    for k in range(40):pool[k*32]=rng.randrange(6);pool[k*32+1]=rng.choice((255,bank,rng.randrange(8)))
    for capped in range(2):
        out=[]
        for slow in range(2):
            p.restore(2+capped*2+slow);a=r.addr('native_pj')&0x1ffff;r.ram[a:a+1280]=pool;r.ram[0x1ff40]=bank;p.run();out.append(r.ram[0x1ff00])
        expected=sum(pool[k*32]==2 or pool[k*32]==3 and pool[k*32+1]==255 for k in range(40)) if capped else sum(pool[k*32]==3 and pool[k*32+1]==bank for k in range(40))
        assert out==[expected,expected],('count',case,capped,out,expected)
for case in range(256):
    p.restore(6);expected=False
    for pi in range(2):
        state=(case>>(pi*4))&3;inv=(case>>(pi*4+2))&3
        r.write('players',state,2,pi*284);r.write('players',inv,1,pi*284+23);expected|=state==1 and inv==0
    p.run();assert bool(r.read('native_boss_contact_possible'))==expected,case
result={'rom_sha256':hashlib.sha256((ROOT/'snes/sidearms_md_snes.sfc').read_bytes()).hexdigest(),'bullet_cases':800,'count_cases':800,'contact_eligibility_cases':256,'passed':True}
(ROOT/'build/qa/projectile-native.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
