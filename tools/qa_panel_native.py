#!/usr/bin/env python3
"""Check native HUD invalidation against the original panel cache."""
import hashlib,json,random
from native_probe import Probe,symbols,le
from test_snes import ROOT
s=symbols();codes=[]
for fn in ('native_panel_probe','native_panel_changed_slow'):
 b=bytes.fromhex('18 fb c2 30 08')
 if fn=='native_panel_probe':b+=bytes.fromhex('e2 20 af 40 ff 7f 48 c2 20')
 b+=b'\xf4'+le(0x7f)+b'\xf4'+le(0xff80)+b'\x22'+le(s[fn],3)+b'\xaf'+le(s['tcc__r0'],3)+bytes.fromhex('8f 04 ff 7f 3b 18 69')+le(5 if fn=='native_panel_probe' else 4)+bytes.fromhex('1b a9 5a a5 8f 08 ff 7f 28 db');codes.append(b)
p=Probe(codes);r=p.r;rng=random.Random(552828)
for case in range(1200):
 old=bytearray(rng.randbytes(54)+bytes([rng.choice((0,4,8,12))]));new=bytearray(old);visible=rng.randrange(2)
 if case%3==0:new[rng.randrange(54)]^=1
 if case%7==0:new[54]=(new[54]+4)&12
 expected=(not visible) or old!=new
 outputs=[]
 for slow in range(2):
  p.restore(slow);a=r.addr('native_hud_snapshot')&0x1ffff;r.ram[a:a+55]=old
  for name,off,n in [('native_panel_last',0,28),('native_panel_score',28,8),('native_panel_stats',36,18),('native_panel_phase',54,1)]:
   b=r.addr('tccs_src/hud.asm_'+name)&0x1ffff;r.ram[b:b+n]=old[off:off+n]
  r.write('tccs_src/hud.asm_cur',visible,1);r.write('frame',new[54]);r.ram[0x1ff40]=visible;r.ram[0x1ff80:0x1ff9c]=new[:28]
  for pi in range(2):
   b=(r.addr('players')&0x1ffff)+pi*284;r.ram[b+32:b+36]=new[28+pi*4:32+pi*4];r.ram[b+14:b+23]=new[36+pi*9:45+pi*9]
  p.run();assert bool(r.ram[0x1ff04])==expected,(case,slow,'invalidation')
  if slow:
   saved=b''
   for name,n in [('native_panel_last',28),('native_panel_score',8),('native_panel_stats',18),('native_panel_phase',1)]:
    b=r.addr('tccs_src/hud.asm_'+name)&0x1ffff;saved+=bytes(r.ram[b:b+n])
  else:saved=bytes(r.ram[a:a+55])
  assert saved==(new if expected else old),(case,'native snapshot')

result={'rom_sha256':hashlib.sha256((ROOT/'snes/sidearms_md_snes.sfc').read_bytes()).hexdigest(),'cases':1200,'passed':True}
(ROOT/'build/qa/panel-native.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
