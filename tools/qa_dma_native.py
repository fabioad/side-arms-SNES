#!/usr/bin/env python3
"""Force partial DMA batches and compare every VRAM byte, including odd sizes."""
import hashlib,json
from native_probe import Probe,symbols,le
from test_snes import ROOT
s=symbols();b=bytes.fromhex('18 fb c2 30 08')
for off in (6,4,2,0):b+=b'\xaf'+le(0x7fff40+off,3)+b'\x48'
b+=b'\x22'+le(s['native_copy'],3)+bytes.fromhex('3b 18 69 08 00 1b')+b'\x22'+le(s['native_next_vblank'],3)
b+=bytes.fromhex('e2 20 a9 00 8f 80 ff 7f c2 20')
b+=bytes.fromhex('a9 bc 02 8f')+le(s['native_dma_budget'],3)+b'\x22'+le(s['native_flush'],3)+bytes.fromhex('a9 5a a5 8f 08 ff 7f 28 db')
p=Probe([b]);r=p.r;out=[]
for mode,n in [('rom',n) for n in (1,32,127,129,2048,4096,22520)]+[('ram',31)]:
 p.restore(0)
 for name in ('queue_count','queue_used','queue_total','native_dma_late','native_dma_overflow','native_dma_splits'):r.write(name,0)
 r.write('paldirty',0,1)
 before=bytearray(r.snapshot_block(b'VRA'));ptr=s['native_wheel0_tiles']+1 if mode=='rom' else 0x7fff80;dest=0x1234
 if mode=='ram':r.ram[0x1ff80:0x1ff9f]=bytes(range(70,101))
 r.ram[0x1ff40:0x1ff48]=le(ptr&65535)+le(ptr>>16)+le(dest)+le(n)
 for frames in range(100):
  r.run(1)
  if bytes(r.ram[0x1ff08:0x1ff0a])==b'\x5a\xa5':break
 else:raise AssertionError(('DMA stalled',n))
 start=ptr&0x3fffff;before[dest*2:dest*2+n]=r.rom[start:start+n] if mode=='rom' else bytes(range(70,101))
 assert r.snapshot_block(b'VRA')==before,('Partial DMA changed VRAM bytes',n)
 assert r.read('queue_count')==0 and r.read('native_dma_late')==0 and r.read('native_dma_overflow')==0
 splits=r.read('native_dma_splits');assert n<700 or splits>0
 out.append({'source':mode,'bytes':n,'splits':splits,'video_frames':frames+1})
result={'rom_sha256':hashlib.sha256((ROOT/'snes/sidearms_md_snes.sfc').read_bytes()).hexdigest(),'cases':out,'passed':True}
(ROOT/'build/qa/dma-native.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
