#!/usr/bin/env python3
"""Long-song SPC regression using direct command requests, not fidelity QA."""
from test_snes import Runner,ROOT
import json

r=Runner(render=False);r.logic(5);results=[]
cases=[(0x21,35000),(0x32,1000),(0x22,35000),(0x32,1000)]
cases += [(x,1000) for x in (0x20,0x23,0x24,0x25,0x26,0x27,0x28,0x29,0x2a,0x2c,0x2e,0x33,0x34,0x35,0x36,0x38)]
for command,frames in cases:
    before=r.read('frame_counter',4)
    r.write('tccs_src/audio.asm_pending',command,1);r.run(frames)
    row={'command':f'{command:02x}','video_frames':frames,'logic_frames':r.read('frame_counter',4)-before,
         'audio_timeouts':r.read('audio_flush_timeouts'),'budget_rejected':r.read('audio_budget_rejected')}
    print(row,flush=True);results.append(row)
    assert row['logic_frames']>frames//2,'SPC load blocked the game loop'
    assert row['audio_timeouts']==0,'SPC command acknowledgment failed'
    assert row['budget_rejected']==(1 if command==0x38 else 0),'Unexpected ARAM overflow'
report={'rom_sha256':r.rom_sha256,'commands':results,'audio_peak':r.audio_peak,
        'fidelity_certified':False,'unsupported_music':['38']}
(ROOT/'build/qa/audio.json').write_text(json.dumps(report,indent=2)+'\n')
