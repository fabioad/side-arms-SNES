#!/usr/bin/env python3
"""Check musical events/jump times survive repacking and only silence is cut."""
from pathlib import Path
import struct
from prepare_music import decode,ROOT

def events(path):
    b=path.read_bytes();o,i,s,p=struct.unpack_from('<4H',b,32)
    orders=list(b[192:192+o]);orders=orders[:orders.index(255)]
    table=192+o+4*(i+s);patterns=[];starts=[];count=0
    for k in orders:
        a=struct.unpack_from('<I',b,table+4*k)[0];n,rows=struct.unpack_from('<HH',b,a)
        starts.append(count);count+=rows;patterns.append(decode(b[a+8:a+8+n],rows))
    normalized=[]
    for pattern in patterns:
        for row in pattern:
            cells=[]
            for ch,v in row:
                fields=dict(v);cmd=fields.get(3,0)
                if cmd&255==2:fields[3]=('jump-to-row',starts[cmd>>8])
                cells.append((ch,fields))
            normalized.append(cells)
    return p,normalized

for original in sorted((ROOT/'sidearms_snes/music').glob('cmd*.it')):
    _,before=events(original);patterns,after=events(ROOT/'build/music'/original.name)
    assert patterns<=64 and before==after,f'{original.name}: musical events or jump timing changed'

def samples(path):
    b=path.read_bytes();o,i,s,_=struct.unpack_from('<4H',b,32);result=[]
    for k in range(s):
        a=struct.unpack_from('<I',b,192+o+4*(i+k))[0]
        n=struct.unpack_from('<I',b,a+48)[0];p=struct.unpack_from('<I',b,a+72)[0]
        result.append(b[p:p+n])
    return result
for before,after in zip(samples(ROOT/'sidearms_snes/res/sfx.it'),samples(ROOT/'build/music/sfx.it'),strict=True):
    assert before.startswith(after) and not any(before[len(after):]),'Non-silent SFX samples were cut'
print('PASS: all tracker notes, durations and jump times preserved; SFX removes only digital silence')
