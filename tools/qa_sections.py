#!/usr/bin/env python3
"""Exercise native section/boss entry paths using the upstream warp hook.

This is a coverage smoke test, not a complete-game/fidelity certification.
The player receives invulnerability so that each encounter can be observed.
"""
from test_snes import Runner,ROOT
import json,collections
r=Runner();r.logic(5);r.press('START');r.logic(10);r.press('START');r.logic(5);r.press('START')
for _ in range(3):r.press('B')
r.logic(450)
assert r.read('flow_state')==7,'Failed to enter Arcade gameplay'
rows=[]
cases=[(0,1),(1,1),(2,1),(3,1),(4,1),(5,0),(6,1),(6,2),(7,1),(7,2),(8,1),(8,2),(9,1)]
for section,boss in cases:
    r.write('dbg_warp',(section+1)|(boss<<8))
    before=r.read('frame_counter',4);n=0;seen=False;phases=collections.Counter()
    while r.read('frame_counter',4)-before<650:
        r.write('players',255,1,r.layout['invuln'])
        r.run(1)
        seen|=bool(r.read('boss_hud',1))
        phases[r.read('native_phase',1)]+=1;n+=1
        if n>90000:
            r.capture(f'stall-section-{section+1}')
            print('STALL',section+1,'phase',r.read('native_phase',1),'audio',r.read('audio_step'),'counter',r.read('frame_counter',4),flush=True)
            raise AssertionError('Section loop stalled')
    row={'rom_sha256':r.rom_sha256,'section':section+1,'boss':boss,'boss_hud_seen':seen,'actual_section':r.read('level')+1,
         'logic_frames':r.read('frame_counter',4)-before,'video_frames':n,
         'logic_hz':round(60*(r.read('frame_counter',4)-before)/n,2),
         'queue_overflow':r.read('native_dma_overflow'),'audio_timeouts':r.read('audio_flush_timeouts'),'sprite_drops':r.read('spr_dbg_dropped',4),'phases':dict(phases)}
    row['late_dma']=r.read('native_dma_late')
    r.capture(f'section-{section+1:02d}-boss-{boss}')
    rows.append(row);print(json.dumps(row),flush=True)
    (ROOT/'build/qa/sections.json').write_text(json.dumps(rows,indent=2)+'\n')
    assert row['actual_section']==section+1,'Warp did not reach requested section'
    assert row['logic_hz']>=30,('Section reference below 30 updates/s',row)
    assert row['queue_overflow']==0,'VRAM queue overflow'
    assert row['audio_timeouts']==0,'SPC700 handshake timed out'
    assert row['late_dma']==0,'DMA exceeded VBlank'
print('Section smoke scenarios completed; full playthrough and fidelity QA remain separate.')
