#!/usr/bin/env python3
"""Boss hit masks, callbacks and repeated same-frame queries against shot geometry."""
import random,json,hashlib
from native_probe import Probe,symbols,le
from test_snes import ROOT
s=symbols();programs=[]
for repeats in (1,2):
 for fn in ('boss_shots','native_boss_shots_slow'):
  b=bytes.fromhex('18 fb c2 30 08')
  for turn in range(repeats):
   b+=b'\xf4'+le(0x7f)+b'\xf4'+le(0xff10)
   for off,n in ((5,1),(4,1),(2,2),(0,2)):
    if n==1:b+=bytes.fromhex('e2 20')
    b+=b'\xaf'+le(0x7fff40+off,3)+b'\x48'
    if n==1:b+=bytes.fromhex('c2 20')
   b+=b'\x22'+le(s[fn],3)+b'\xaf'+le(s['tcc__r0'],3)+b'\x8f'+le(0x7fff04+turn*2,3)+bytes.fromhex('3b 18 69 0a 00 1b')
  b+=bytes.fromhex('a9 5a a5 8f 08 ff 7f 28 db');programs.append(b)
p=Probe(programs);r=p.r;rng=random.Random(160030);hits=0
for case in range(1200):
 repeats=1+case%2;py=rng.randrange(-24,280);px=rng.randrange(-32,480);c=rng.randrange(1,100);d=rng.randrange(1,100);shift=rng.randrange(-64,128);auto=int(case%13==0)
 block=bytearray(r.layout['player_size']*2)
 for pi in range(2):
  for k in range(9):
   at=pi*r.layout['player_size']+r.layout['shots']+k*r.layout['shot_size']
   x=rng.randrange(-32,370);y=rng.randrange(-32,260);active=rng.randrange(3);hw=rng.randrange(24);hh=rng.randrange(24);pierce=rng.randrange(2)
   block[at:at+4]=le(x&65535)+le(y&65535);block[at+8]=active;block[at+12:at+15]=bytes((hw,hh,pierce))
 expected_block=bytearray(block);expected_counts=[];who=0
 for turn in range(repeats):
  expected=auto
  if auto:who=s['players']
  for pi in range(2):
   for k in range(9):
    at=pi*r.layout['player_size']+r.layout['shots']+k*r.layout['shot_size'];shot=expected_block[at:at+22]
    x=int.from_bytes(shot[:2],'little',signed=True);y=int.from_bytes(shot[2:4],'little',signed=True)
    if shot[8]!=1 or abs(py-y-16)>=c+shot[13] or abs(px-x-96-shift)>=d+shot[12]:continue
    expected+=1;who=s['players']+pi*r.layout['player_size'];hits+=1
    if not shot[14]:expected_block[at+8]=2;expected_block[at+10]=16;expected_block[at+16:at+19]=bytes((28,0,5))
  expected_counts.append(expected)
 for mode in range(2):
  p.restore((repeats-1)*2+mode);a=r.addr('players')&0x1ffff;r.ram[a:a+len(block)]=block
  r.write('native_live_shots',18);r.write('boss_shift',shift&65535);r.write('boss_dbg_autohit',auto,1);r.ram[0x1ff10:0x1ff14]=bytes(4)
  r.ram[0x1ff40:0x1ff46]=le(py&65535)+le(px&65535)+bytes((c,d));p.run()
  actual=[r.ram[0x1ff04+turn*2] for turn in range(repeats)];actual_who=int.from_bytes(bytes(r.ram[0x1ff10:0x1ff14]),'little')
  assert actual==expected_counts,(case,mode,actual,expected_counts)
  assert actual_who==who,(case,mode,actual_who,who)
  assert bytes(r.ram[a:a+len(block)])==expected_block,(case,mode,'shot mutations')
result={'rom_sha256':hashlib.sha256((ROOT/'snes/sidearms_md_snes.sfc').read_bytes()).hexdigest(),'cases':1200,'same_frame_repeat_cases':600,'hits':hits,'passed':True}
(ROOT/'build/qa/boss-contacts.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
