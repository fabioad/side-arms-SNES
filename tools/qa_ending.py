#!/usr/bin/env python3
"""Final boss, congratulations/staff phases, ranking insertion and reset.

Uses the source warp, invulnerability and auto-hit hooks explicitly.
"""
from test_snes import Runner,ROOT
import json

r=Runner(render=False);r.logic(5);r.press('START');r.logic(10);r.press('START');r.logic(5);r.press('START')
for _ in range(3):r.press('B')
r.logic(450);r.write('dbg_warp',0x10a);r.write('boss_dbg_autohit',1,1)
end='tccs_src/logic/boss_final.asm_end';seen=[];last=None;idle=0;tick=r.read('frame_counter',4)
for n in range(80000):
    r.write('players',255,1,r.layout['invuln']);r.write('players',9,1,r.layout['lives']);r.run(1)
    phase=r.read(end,1,4);now=r.read('frame_counter',4);state=r.read('flow_state')
    if r.read(end,1) and phase!=last:
        seen.append(phase);last=phase
        r.logic(2) # let the newly queued text reach the PPU before the screenshot
        r.capture(f'ending-phase-{phase}');print('ending phase',phase,'logic',now,flush=True)
    idle=idle+1 if now==tick else 0;tick=now
    assert idle<1200,'Final boss/ending loop stalled'
    assert state in (7,2),'Invalid flow state during ending: '+str(state)
    assert r.read('audio_flush_timeouts')==0
    assert r.read('native_dma_overflow')==0
    if state==2:
        assert r.read(end,1,1)==1,'Returned before ending.done'
        assert set(range(5)).issubset(seen),'Congratulations/staff phases missing'
        break
else:raise AssertionError('Ending did not finish')
rank=[r.read('ranking',4,i*8) for i in range(5)]
assert rank==sorted(rank,reverse=True),'Ranking insertion order corrupted'
assert rank[0]>100000,'Final boss score did not enter the ranking'
r.logic(10);r.capture('ending-return');r.core.retro_reset();r.run(500)
assert [r.read('ranking',4,i*8) for i in range(5)]==rank,'Ranking did not persist across reset'
result={'rom_sha256':r.rom_sha256,'qa_warp':True,'qa_invulnerability':True,'qa_auto_hit':True,'ending_phases':seen,
        'returned_to_warning':True,'ranking':rank,'ranking_survived_reset':True,'complete':True}
(ROOT/'build/qa/ending.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
