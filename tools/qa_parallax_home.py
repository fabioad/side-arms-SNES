#!/usr/bin/env python3
"""Measure Home parallax with real gameplay, invulnerability and section warps."""
import argparse,json
p=argparse.ArgumentParser();p.add_argument('--off',action='store_true');a=p.parse_args()
from test_snes import Runner,ROOT
r=Runner();r.logic(5);r.press('DOWN');r.press('START');r.logic(10)
if a.off:
 for _ in range(2):r.press('DOWN')
 r.press('Y')
 for _ in range(6):r.press('DOWN')
 r.press('RIGHT');r.press('B')
 assert r.read('home_cfg',1,5)==0
r.press('START');r.logic(20)
for _ in range(3):r.press('B')
r.logic(550);assert r.read('flow_state')==7
out=[]
for section in (1,3,5,6):
 if section!=1:r.write('dbg_warp',section);r.logic(80)
 start=r.read('frame_counter',4);video=r.frames;modes=set();black=0
 while r.frames-video<1500:
  r.write('players',255,1,r.layout['invuln']);r.run(1);modes.add(r.read('par_dbg_mode',1));black+=not bool(r.frame.max())
 missing={k:sorted({r.read('native_'+k+'_missing_keys',2,i*2) for i in range(min(256,r.read('native_'+k+'_missing_count')))}) for k in ('sprite','big')}
 result={'missing_patterns':missing,'section':section,'logic_hz':60*(r.read('frame_counter',4)-start)/(r.frames-video),'modes':sorted(modes),'black':black,'late_dma':r.read('native_dma_late'),'overflow':r.read('native_dma_overflow')}
 print(result,flush=True);out.append(result);r.capture('parallax-home-'+('off' if a.off else 'on')+'-section-'+str(section))
 assert not black and not result['late_dma'] and not result['overflow']
 assert result['logic_hz']>=30,('Home reference below 30 updates/s',result)
 assert modes==({0} if a.off else {2} if section in (3,6) else {1})
(ROOT/('build/qa/parallax-home-'+('off' if a.off else 'on')+'.json')).write_text(json.dumps({'rom_sha256':r.rom_sha256,'parallax_on':not a.off,'qa_invulnerability_and_warp':True,'cases':out},indent=2)+'\n')
