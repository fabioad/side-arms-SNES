#!/usr/bin/env python3
"""SPC ARAM budgets from the exact HiROM soundbank emitted by smconv."""
from pathlib import Path
import sys
b=Path(sys.argv[1]).read_bytes()
def address(table,index):
    p=table+index*3
    return int.from_bytes(b[p:p+2],'little')+b[p+2]*65536
def sample_size(index):
    p=address(0x184,index)
    return (int.from_bytes(b[p:p+2],'little')+1)&~1
n=int.from_bytes(b[2:4],'little');sizes=[]
for i in range(n):
    p=address(4,i);words=int.from_bytes(b[p:p+2],'little');ns=int.from_bytes(b[p+2:p+4],'little')
    ids=[int.from_bytes(b[p+4+j*2:p+6+j*2],'little') for j in range(ns)]
    sizes.append(words*2+sum(sample_size(j) for j in ids))
effects=sum(sample_size(i) for i in (0,1,2,3,4,5,7))
out=['#ifndef NATIVE_SOUND_META_H','#define NATIVE_SOUND_META_H',
     f'#define NATIVE_EFFECT_BYTES {effects}',f'#define NATIVE_INTRO_BYTES {sample_size(6)}',
     # SetupEcho clears page FE even with EDL=0. FF holds the TCALL vector.
     '#define NATIVE_MUSIC_LIMIT (0xFE00 - 0x1A00)',
     'static const u16 native_music_bytes[]={'+','.join(map(str,sizes))+'};','#endif']
Path(sys.argv[2]).write_text('\n'.join(out)+'\n')
print('ARAM music sizes:',sizes,'resident effects:',effects)
