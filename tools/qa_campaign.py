#!/usr/bin/env python3
"""End-to-end progression with explicit QA invulnerability and boss auto-hit.

Exercises transitions and ending/record code; does not certify normal difficulty.
"""
import argparse,json
from test_snes import Runner,ROOT
p=argparse.ArgumentParser();p.add_argument('--rush',action='store_true');args=p.parse_args()
r=Runner(render=False);r.logic(5)
if args.rush:
    r.press('DOWN');r.press('START');r.logic(5);r.press('DOWN');r.press('START');r.logic(100)
    assert r.read('flow_state')==12,'Boss Rush did not start'
else:
    r.press('START');r.logic(10);r.press('START');r.logic(5);r.press('START')
    for _ in range(3):r.press('B')
    r.logic(450);assert r.read('flow_state')==7,'Arcade gameplay did not start'
r.write('boss_dbg_autohit',1,1)
seen=[];last=None;checkpoint=r.read('frame_counter',4);idle=0;last_tick=checkpoint;start=r.frames
mode='rush' if args.rush else 'campaign'
result={'rom_sha256':r.rom_sha256,'mode':mode,'headless_rendering':True,'qa_invulnerability':True,'qa_infinite_lives':True,'qa_auto_hit':True,'sections':seen,'complete':False}
for n in range(1500000):
    r.write('players',255,1,r.layout['invuln']);r.write('players',9,1,r.layout['lives']);r.run(1,['B'])
    sec=r.read('level')+1;tick=r.read('frame_counter',4);state=r.read('flow_state')
    if sec!=last:
        print('section',sec,'logic',tick,'video',r.frames-start,flush=True)
        seen.append(sec);last=sec;r.capture(f'{mode}-section-{sec:02d}')
    if tick==last_tick:idle+=1
    else:last_tick=tick;idle=0
    if idle>=1200:
        print('STALL',sec,'phase',r.read('native_phase',1),'audio_step',hex(r.read('audio_step')),'game',tick,flush=True)
        r.capture(mode+'-stall')
        raise AssertionError('Main loop stalled')
    assert r.read('native_dma_overflow')==0,'VRAM queue overflow'
    assert r.read('audio_flush_timeouts')==0,f'SPC700 timed out in section {sec}, command {r.read("audio_last_command",1):02x}'
    if args.rush and state==13:
        result['bosses']=r.read('rush_best',1)
        assert result['bosses']==12,'Boss Rush ended before all twelve bosses'
        result['complete']=True;break
    if not args.rush and state!=7:
        assert 10 in seen,f'Campaign ended early in section {sec}, flow {state}'
        assert state in (2,9),f'Invalid post-ending flow state {state}'
        assert r.read('tccs_src/logic/boss_final.asm_end',1,1)==1,'Ending did not complete'
        result['complete']=True;break
    if tick-checkpoint>=5000:
        checkpoint=tick;print('checkpoint',tick,'section',sec,flush=True)
        result.update(logic_frames=tick,video_frames=r.frames-start)
        (ROOT/f'build/qa/{mode}.json').write_text(json.dumps(result,indent=2)+'\n')
else:raise AssertionError('Progression did not finish within the scenario budget')
result.update(logic_frames=r.read('frame_counter',4),video_frames=r.frames-start,flow_state=r.read('flow_state'),
              audio_peak=r.audio_peak,audio_timeouts=r.read('audio_flush_timeouts'),audio_budget_rejected=r.read('audio_budget_rejected'),sprite_drops=r.read('spr_dbg_dropped',4))
r.capture(mode+'-ending')
(ROOT/f'build/qa/{mode}.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result),flush=True)
