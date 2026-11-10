#!/usr/bin/env python3
"""Measure the same menu interactions or the complete, unskipped Earth intro."""
import argparse,json
from test_snes import Runner,ROOT
p=argparse.ArgumentParser();p.add_argument('--rom-path');p.add_argument('--scenario',choices=['menu','intro'],required=True);p.add_argument('--label',default='after');a=p.parse_args()
r=Runner(rom_path=a.rom_path);r.logic(5)
result={'rom_sha256':r.rom_sha256,'scenario':a.scenario,'boot_video_frames':r.frames}
if a.scenario=='menu':
    r.press('DOWN');r.press('START');r.logic(5)
    for _ in range(2):r.press('DOWN')
    r.press('Y');r.logic(5);assert r.read('flow_state')==1
    r.press('DOWN');r.press('UP')
    start=r.read('frame_counter',4);video=r.frames
    for _ in range(10):r.press('DOWN');r.press('UP')
    ticks=r.read('frame_counter',4)-start;elapsed=r.frames-video
    result.update(logic_ticks=ticks,video_frames=elapsed,logic_hz=60*ticks/elapsed)
    r.capture('ui-menu-'+a.label)
else:
    r.press('START');r.logic(10);r.press('START');r.logic(5);r.press('START')
    for _ in range(3):r.press('B')
    assert r.read('flow_state')==6,'Intro did not start'
    start=r.read('frame_counter',4);video=r.frames;scenes=set()
    while r.read('flow_state')==6:
        r.run(1);scene=r.read('scene_visible')
        if scene<16:
            if scene not in scenes and scene in (1,3,15):r.capture('ui-intro-'+a.label+'-'+str(scene))
            scenes.add(scene)
        assert r.frames-video<60000,'Intro stalled'
    ticks=r.read('frame_counter',4)-start;elapsed=r.frames-video
    assert r.read('flow_state')==7,'Intro did not lead to gameplay'
    assert scenes==set(range(1,16)),('Intro animation frames missing',scenes)
    result.update(logic_ticks=ticks,video_frames=elapsed,logic_hz=60*ticks/elapsed,scenes=sorted(scenes),reached_gameplay=True)
result.update(late_dma=r.read('native_dma_late'),dma_overflow=r.read('native_dma_overflow'),audio_timeouts=r.read('audio_flush_timeouts'))
assert result['late_dma']==0 and result['dma_overflow']==0 and result['audio_timeouts']==0
assert result['logic_hz']<=60.5,'UI simulation runs faster than the display'
if a.rom_path is None:assert result['logic_hz']>=30,'UI workload must reach 30 updates/s'
(ROOT/f'build/qa/ui-{a.scenario}-{a.label}.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
