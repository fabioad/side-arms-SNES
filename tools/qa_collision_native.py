#!/usr/bin/env python3
"""Compare the actual 65816 collision helpers with an independent Python model.

Only the in-memory test ROM gains a tiny trampoline in unused bank 55. The
production cartridge is unchanged. Each case restores the same Snes9x state.
"""
import ctypes as C
import random,re,json,hashlib
from test_snes import Runner,ROOT
symbols={}
for line in (ROOT/'snes/sidearms_md_snes.sym').read_text().splitlines():
    m=re.match(r'([0-9a-fA-F]+) (\S+)$',line)
    if m:symbols[m[2]]=int(m[1],16)
def le(n,size=2):return n.to_bytes(size,'little')
e=symbols['en_big']
codes=[]
for big in range(2):
    # Explicit native mode avoids depending on hidden CPU mode flags in the snapshot.
    code=bytearray.fromhex('18 fb c2 30 08')
    for fn,result in (('native_enemy_contact',0x7fff04),('native_collision_tick',0x7fff06),('native_enemy_terrain',0x7fff0c)):
        code+=b'\xf4'+le(big)+b'\xf4'+le(e>>16)+b'\xf4'+le(e&65535)
        code+=b'\x22'+le(symbols[fn],3)+b'\xaf'+le(symbols['tcc__r0'],3)+b'\x8f'+le(result,3)
        code+=bytes.fromhex('3b 18 69 06 00 1b')
    code+=b'\x22'+le(symbols['native_collect_contacts'],3)+b'\xaf'+le(symbols['tcc__r0'],3)+b'\x8f'+le(0x7fff0e,3)
    code+=bytes.fromhex('a9 5a a5 8f 08 ff 7f 28 db')
    codes.append(code)
def patch(raw):
    raw=bytearray(raw);start=55*65536
    for i,code in enumerate(codes):
        off=start+i*256
        assert len(set(raw[off:off+len(code)]))==1,'Test trampoline bank is occupied'
        raw[off:off+len(code)]=code
    return bytes(raw)
r=Runner(False,rom_patch=patch);r.logic(5)
r.core.retro_serialize_size.restype=C.c_size_t
size=r.core.retro_serialize_size();buf=C.create_string_buffer(size)
r.core.retro_serialize.argtypes=[C.c_void_p,C.c_size_t]
assert r.core.retro_serialize(buf,size)
base=bytearray(buf.raw);pos=base.index(b'\n')+1
while base[pos:pos+3]!=b'REG':pos+=11+int(base[pos+4:pos+10])
pos+=11
base[pos]=0xf7;base[pos+14:pos+16]=b'\0\0'
base[pos+8:pos+10]=(0x1ff0).to_bytes(2,'big')
base[pos+6:pos+8]=b'\0\0'
states=[]
for big in range(2):
    base[pos+14:pos+16]=(big*256).to_bytes(2,'big')
    states.append(C.create_string_buffer(bytes(base)))
r.core.retro_unserialize.argtypes=[C.c_void_p,C.c_size_t];r.core.retro_unserialize.restype=C.c_bool
rng=random.Random(65816);cases=1500;touches=0
for case in range(cases):
    big=rng.randrange(2)
    assert r.core.retro_unserialize(states[big],size)
    frame=rng.randrange(65536);combined=rng.randrange(3)
    scrollx=rng.randrange(4096);scrolly=rng.randrange(4096)
    r.write('level',scrollx,2,4);r.write('level',scrolly,2,6)
    x=rng.randrange(-100,401);y=rng.randrange(-32,256);ox=rng.randrange(256)
    hh=rng.randrange(49);hw=rng.randrange(33);item=rng.choice((0,0,1,6))
    r.write('en_big',x&65535,2,4);r.write('en_big',y&65535,2,6)
    r.write('en_big',ox,1,29);r.write('en_big',hh,1,20);r.write('en_big',hw,1,21);r.write('en_big',item,1,17)
    r.write('frame',frame);r.write('combined',combined,1)
    r.ram[0x1ff00]=big;r.ram[0x1ff08:0x1ff0a]=[0,0]
    expected=65535;oy=(y+16)&255
    details=[];snapshots=[];has_shot=False
    for pi in range(2):
        alive=rng.choice((0,1,1));status=rng.choice((0,1,1,2));inv=rng.choice((0,0,1,255))
        py=(oy+rng.randrange(-35,36))&255;px=(ox+rng.randrange(-25,26))&255
        r.write('pl_alive',alive,1,pi);r.write('pl_y',py,1,pi);r.write('pl_x2',px,1,pi)
        r.write('players',status,2,pi*r.layout['player_size'])
        r.write('players',inv,1,pi*r.layout['player_size']+r.layout['invuln'])
        playerx=rng.randrange(-32768,32768);playery=rng.randrange(-32768,32768)
        r.write('players',playerx&65535,2,pi*r.layout['player_size']+r.layout['x'])
        r.write('players',playery&65535,2,pi*r.layout['player_size']+r.layout['y'])
        snapshots.append((int(status==1),(playery+16)&255,(((playerx+96)&65535)>>1)&255))
        for shot in range(9):
            active=1 if case%3==0 and shot==(case%9) and pi==(case%2) else rng.choice((0,2))
            has_shot|=active==1
            r.write('players',active,1,pi*r.layout['player_size']+r.layout['shots']+shot*r.layout['shot_size']+r.layout['shot_active'])
        details.append((alive,status,inv,py,px))
        py=(py+(0 if big else 8))&255;px=(px+(0 if big else 4))&255
        if expected==65535 and alive and status==1 and abs(py-oy)<hh and abs(px-ox)<hw:
            if (not big and item) or not inv:expected=pi
    tick=int((frame&1)==big or (big and combined!=0))
    r.run(1)
    assert int.from_bytes(bytes(r.ram[0x1ff08:0x1ff0a]),'little')==0xa55a,('Trampoline did not finish',case,big,r.snapshot_block(b'REG').hex(),list(r.ram[0x1ff04:0x1ff0c]))
    actual=int.from_bytes(bytes(r.ram[0x1ff04:0x1ff06]),'little')
    actual_tick=int.from_bytes(bytes(r.ram[0x1ff06:0x1ff08]),'little')
    assert actual==expected,(case,'contact',actual,expected,big,y,ox,hh,hw,item,details)
    assert actual_tick==tick,(case,'cadence',actual_tick,tick)
    assert r.read('en_big',1,29)==((((x+96)&65535)>>1)&255 if tick else ox)
    wx=(scrollx+x+96+(16 if big else 24))&4095
    wy=(scrolly+((y+16+(16 if big else 8))&255))&4095
    address=symbols['terrain'];offset=((address>>16)&63)*65536+(address&65535)
    expected_terrain=int(bool(r.rom[offset+(wy>>4)*32+(wx>>7)]&(0x80>>((wx>>4)&7))))
    assert int.from_bytes(bytes(r.ram[0x1ff0c:0x1ff0e]),'little')==expected_terrain
    assert int.from_bytes(bytes(r.ram[0x1ff0e:0x1ff10]),'little')==int(has_shot)
    for pi in range(2):
        assert (r.read('pl_alive',1,pi),r.read('pl_y',1,pi),r.read('pl_x2',1,pi))==snapshots[pi]
    touches+=expected!=65535
assert touches>50,'Insufficient positive-contact cases'
result={'cases':cases,'contacts':touches,'production_rom_sha256':hashlib.sha256((ROOT/'snes/sidearms_md_snes.sfc').read_bytes()).hexdigest(),'passed':True}
(ROOT/'build/qa/native-collision.json').write_text(json.dumps(result,indent=2)+'\n')
print(result)
