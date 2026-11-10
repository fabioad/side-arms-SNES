#!/usr/bin/env python3
"""Repeatable sustained wheel/final boss workloads, with explicit QA hooks."""
import json,subprocess,sys
from test_snes import ROOT
cases=[(2,True,False),(8,True,False),(10,False,True)]
out=[]
for section,home,pulse in cases:
 label=f'boss-performance-{section}';cmd=[sys.executable,str(ROOT/'tools/profile_native.py'),'--section',str(section),'--boss','1','--frames','6000','--label',label]
 if home:cmd.append('--home')
 if pulse:cmd.append('--pulse')
 subprocess.run(cmd,check=True,cwd=ROOT)
 row=json.loads((ROOT/f'build/qa/{label}.json').read_text());out.append(row)
 assert row['flow_state']==7 and row['level']==section and row['boss_kind']!=0,row
 assert row['logic_hz']>=30,row
 assert not row['late_dma'] and not row['overflow'],row
 assert not any(row['missing_patterns'].values()),row
 if home:assert row['max_gap']<20,('Recurring wheel stalls returned',row)
(ROOT/'build/qa/boss-performance.json').write_text(json.dumps(out,indent=2)+'\n')
print('PASS: sustained large bosses and repeated final-boss firing reach 30 updates/s')
