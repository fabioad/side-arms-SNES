#!/usr/bin/env python3
"""Check native fills, byte guards, returned pointers and wrapped zone lookup."""
import hashlib,json,random,re,struct
from native_probe import Probe,symbols,le
from test_snes import ROOT
s=symbols();codes=[]
for fn,offsets,cleanup in [('native_memset',(6,4,2,0),8),('native_bg_entry',(2,0),4),('terrain_solid',(2,0),4)]:
 b=bytes.fromhex('18 fb c2 30 08')
 for off in offsets:b+=b'\xaf'+le(0x7fff40+off,3)+b'\x48'
 b+=b'\x22'+le(s[fn],3)+b'\xaf'+le(s['tcc__r0'],3)+bytes.fromhex('8f 00 ff 7f')+b'\xaf'+le(s['tcc__r0h'],3)+bytes.fromhex('8f 02 ff 7f 3b 18 69')+le(cleanup)+bytes.fromhex('1b a9 5a a5 8f 08 ff 7f 28 db');codes.append(b)
p=Probe(codes);r=p.r;rng=random.Random(150016);sizes=(0,1,2,3,15,16,17,31,32,33,255,256,257,1023,1024,2048,32768)
for case in range(500):
 p.restore(0);n=sizes[case] if case<len(sizes) else rng.randrange(3000);value=rng.randrange(65536);ptr=0x7f0100
 start=(ptr&0x1ffff)-16;r.ram[start:start+n+32]=bytes([85])*(n+32)
 r.ram[0x1ff40:0x1ff48]=le(ptr&65535)+le(ptr>>16)+le(value)+le(n)
 for _ in range(20):
  r.run(1)
  if bytes(r.ram[0x1ff08:0x1ff0a])==b'\x5a\xa5':break
 else:raise AssertionError(('Fill stalled',case,n))
 assert bytes(r.ram[start:start+n+32])==bytes([85])*16+bytes([value&255])*n+bytes([85])*16,(case,n)
 assert int.from_bytes(bytes(r.ram[0x1ff00:0x1ff04]),'little')==ptr
zones=[tuple(map(int,m)) for m in re.findall(r'\{(\d+), (\d+), (\d+), (\d+), (\d+), zone\d+_tiles',(ROOT/'src/gen/zones.c').read_text())][:24]
for case in range(1500):
 p.restore(1);z=rng.randrange(24);x=rng.randrange(-200,250);y=rng.randrange(-200,250);x0,y0,w,h,n=zones[z]
 rect=le(x0)+le(y0)+le(w)+le(h)+le(n);a=r.addr('native_zone_rect')&0x1ffff;r.ram[a:a+10]=rect
 r.write('native_zone_map',s[f'zone{z}_map'],4);r.write('native_bg_frame_fallback',0)
 r.ram[0x1ff40:0x1ff44]=le(x&65535)+le(y&65535);p.run()
 cells=struct.unpack('>'+str(w*h)+'H',(ROOT/f'res/generated/zone{z}_map.bin').read_bytes());xx=x&127;yy=y&127
 expected=cells[(yy-y0)*w+xx-x0] if x0<=xx<x0+w and y0<=yy<y0+h else 65535
 actual=int.from_bytes(bytes(r.ram[0x1ff00:0x1ff02]),'little');assert actual==expected,(case,z,x,y,actual,expected)
terrain=(ROOT/'snes/res/terrain.bin').read_bytes()
for case in range(4000):
 p.restore(2);x=rng.randrange(4096) if case%2 else rng.randrange(-32768,32768);y=rng.randrange(4096) if case%2 else rng.randrange(-32768,32768)
 r.ram[0x1ff40:0x1ff44]=le(x&65535)+le(y&65535);p.run()
 expected=((terrain[(y>>4)*32+(x>>7)]>>(7-((x>>4)&7)))&1) if 0<=x<4096 and 0<=y<4096 else 0
 assert int.from_bytes(bytes(r.ram[0x1ff00:0x1ff02]),'little')==expected,(case,x,y,'world terrain')
result={'rom_sha256':hashlib.sha256((ROOT/'snes/sidearms_md_snes.sfc').read_bytes()).hexdigest(),'fill_cases':500,'map_cases':1500,'world_terrain_cases':4000,'passed':True}
(ROOT/'build/qa/memory-native.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
