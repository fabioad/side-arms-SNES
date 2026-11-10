#!/usr/bin/env python3
"""Repack the supplied IT sequences into SNESMOD's 64-pattern address table.

Keep every tracker row, note and instrument. Groups stop at jump destinations,
so an intro/loop boundary survives merging adjacent 128-row patterns.
"""
from pathlib import Path
import struct

ROOT=Path(__file__).resolve().parents[1]

def decode(blob, count):
    masks=[0]*64;previous=[[0]*4 for _ in range(64)];rows=[];row=[];p=0
    while len(rows)<count:
        token=blob[p];p+=1
        if not token:rows.append(row);row=[];continue
        ch=(token-1)&63
        if token&128:masks[ch]=blob[p];p+=1
        mask=masks[ch];values={}
        for field in range(4):
            if mask&(1<<field):
                n=2 if field==3 else 1
                previous[ch][field]=int.from_bytes(blob[p:p+n],'little');p+=n
                values[field]=previous[ch][field]
            elif mask&(16<<field):values[field]=previous[ch][field]
        row.append((ch,values))
    assert p==len(blob),'Unexpected trailing packed pattern data'
    return rows

def encode(rows):
    data=bytearray()
    for row in rows:
        for ch,values in row:
            data.extend((128+ch+1,sum(1<<f for f in values)))
            for field,value in sorted(values.items()):data.extend(value.to_bytes(2 if field==3 else 1,'little'))
        data.append(0)
    return data

def repack(source,dest):
    data=bytearray(source.read_bytes());orders,ins,samples,patterns=struct.unpack_from('<4H',data,32)
    sequence=list(data[192:192+orders]);sequence=sequence[:sequence.index(255)]
    assert sequence==list(range(patterns)),f'{source}: expected linear source orders'
    table=192+orders+4*(ins+samples);rows=[];targets={0}
    for i in range(patterns):
        off=struct.unpack_from('<I',data,table+4*i)[0]
        size,count=struct.unpack_from('<HH',data,off)
        pattern=decode(data[off+8:off+8+size],count);rows.append(pattern)
        for row in pattern:
            for _,v in row:
                cmd=v.get(3,0)
                assert cmd&255!=3,'Pattern break needs a separate remapping'
                if cmd&255==2:targets.add(cmd>>8)
    groups=[];mapping={}
    for i,row in enumerate(rows):
        if not groups or i in targets or len(groups[-1])+len(row)>256:groups.append([])
        mapping[i]=len(groups)-1;groups[-1].extend(row)
    assert len(groups)<=64,f'{source}: still exceeds SNESMOD pattern table'
    data[192:192+orders]=bytes(range(len(groups)))+bytes([255])*(orders-len(groups))
    struct.pack_into('<H',data,38,len(groups))
    for i,group in enumerate(groups):
        for row in group:
            for _,v in row:
                cmd=v.get(3,0)
                if cmd&255==2:v[3]=2+(mapping[cmd>>8]<<8)
        packed=encode(group);assert len(packed)<65536
        struct.pack_into('<I',data,table+4*i,len(data))
        data.extend(struct.pack('<HHI',len(packed),len(group),0)+packed)
    dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
    return {'name':source.name,'source_patterns':patterns,'patterns':len(groups),'rows':sum(map(len,groups))}

def trim_sfx(source,dest):
    """Drop recorded digital silence, retaining one silent DSP block.

    Non-looping PCM ends in silence anyway. Keeping that silence in ARAM
    needlessly overlaps the driver's reserved echo page on larger songs.
    """
    data=bytearray(source.read_bytes());orders,ins,samples,_=struct.unpack_from('<4H',data,32)
    report=[]
    for i in range(samples):
        p=struct.unpack_from('<I',data,192+orders+4*(ins+i))[0]
        assert data[p:p+4]==b'IMPS' and not data[p+17]&0x12,'Expected non-looping 8-bit PCM'
        n=struct.unpack_from('<I',data,p+48)[0];offset=struct.unpack_from('<I',data,p+72)[0]
        end=n
        while end and data[offset+end-1]==0:end-=1
        kept=min(n,((end+15)//16+1)*16)
        struct.pack_into('<I',data,p+48,kept)
        report.append({'sample':i,'source_samples':n,'samples':kept})
    dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
    return report

if __name__=='__main__':
    import json
    files=sorted((ROOT/'sidearms_snes/music').glob('cmd*.it'))
    report=[repack(p,ROOT/'build/music'/p.name) for p in files]
    trim_sfx(ROOT/'sidearms_snes/res/sfx.it',ROOT/'build/music/sfx.it')
    (ROOT/'build/music/manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))
