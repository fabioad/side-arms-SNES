#!/usr/bin/env python3
"""Sample emulated CPU locations at video boundaries, with logical tick gaps."""
import argparse,bisect,collections,json,re
from pathlib import Path
from test_snes import Runner,ROOT
p=argparse.ArgumentParser();p.add_argument('--home',action='store_true');p.add_argument('--section',type=int,default=2);p.add_argument('--boss',type=int,default=1);p.add_argument('--frames',type=int,default=3000);p.add_argument('--rom-path');p.add_argument('--label',default='profile');p.add_argument('--fire',action='store_true');p.add_argument('--pulse',action='store_true');a=p.parse_args()
r=Runner(False,rom_path=a.rom_path);r.logic(5)
if a.home:
 r.press('DOWN');r.press('START');r.logic(10);r.press('START');r.logic(20)
else:r.press('START');r.logic(10);r.press('START');r.logic(5);r.press('START')
for _ in range(3):r.press('B')
r.logic(450);r.write('dbg_warp',a.section|(a.boss<<8));r.logic(100)
path=Path(a.rom_path).with_suffix('.symfull') if a.rom_path else ROOT/'snes/sidearms_md_snes.symfull'
if not path.exists():path=Path(a.rom_path).with_suffix('.sym') if a.rom_path else ROOT/'snes/sidearms_md_snes.sym'
entries=[]
for line in path.read_text().splitlines():
 m=re.match(r'([0-9a-fA-F]+) (.*SECTIONSTART_.*)',line)
 if m:entries.append((int(m[1],16),m[2]))
entries.sort();addresses=[v[0] for v in entries]
dma=collections.Counter();upload=collections.Counter();pcs=collections.Counter();phases=collections.Counter();gaps=[];prev=r.read('frame_counter',4);last=r.frames;start=prev;video=r.frames
for _ in range(a.frames):
 r.write('players',255,1,r.layout['invuln']);r.run(1,['B'] if (a.pulse and r.read('frame_counter',4)&3<2) or (a.fire and not a.pulse) else ())
 f=r.read('frame_counter',4)
 if f!=prev:
  gaps.append(r.frames-last);prev=f;last=r.frames;dma[r.read('native_dma_bytes')]+=1;upload[r.read('tccs_src/sprites.asm_uploads')]+=1
 phase=r.read('native_phase',1);phases[phase]+=1
 if phase in (1,2,3,5,6):
  reg=r.snapshot_block(b'REG');pc=(reg[0]<<16)|int.from_bytes(reg[14:16],'big');pc=(pc|0xc00000) if pc>>16<0x40 and pc&0x8000 else pc;idx=bisect.bisect_right(addresses,pc)-1
  name=entries[idx][1] if idx>=0 else hex(pc);pcs[name]+=1
missing={k:sorted({r.read('native_'+k+'_missing_keys',2,i*2) for i in range(min(256,r.read('native_'+k+'_missing_count')))}) for k in ('sprite','big') if 'native_'+k+'_missing_count' in r.symbols}
result={'missing_patterns':missing,'rom_sha256':r.rom_sha256,'section':a.section,'boss':a.boss,'home':a.home,'fire':a.fire or a.pulse,'pulse':a.pulse,'logic_hz':60*(prev-start)/a.frames,'phases':dict(phases),'tick_gaps':dict(collections.Counter(gaps)),'dma_bytes':dict(dma),'sprite_uploads':dict(upload),'max_gap':max(gaps,default=0),'cpu_samples':pcs.most_common(30),'late_dma':r.read('native_dma_late'),'overflow':r.read('native_dma_overflow'),'flow_state':r.read('flow_state'),'boss_kind':r.read('tccs_src/logic/boss.asm_kind',1),'level':r.read('level')+1,'boss_kills':r.read('boss_kills')}
(ROOT/('build/qa/'+a.label+'.json')).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
