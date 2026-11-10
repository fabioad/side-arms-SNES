#!/usr/bin/env python3
"""Place exported C const objects in HiROM instead of 816-tcc's copied data.

816-tcc already emits far references for these symbols. Only their placement
changes; the initialized bytes and pointer relocations remain assembler input.
"""
from pathlib import Path
import re,sys

def convert(path):
    source=path.with_suffix('.c')
    if not source.exists(): return
    constants=set(re.findall(r'^const\s+[^;=\n]+?\b(\w+)\s*\[[^;=]*\]\s*=',source.read_text(),re.M))
    if not constants:return
    s=path.read_text(); lines=s.splitlines(); decls=[]; inram=False
    for line in lines:
        if line.startswith('.RAMSECTION') and 'globram.data' in line: inram=True
        elif line.startswith('.ENDS'): inram=False
        elif inram:
            m=re.match(r'(\S+)\s+dsb\s+(\d+)',line,re.I)
            if m: decls.append((m[1],int(m[2])))
    if not decls:return
    result=[]; exported=[]; indata=False; inram=False; obj=0; consumed=0; chunks=[]
    def finish():
        nonlocal chunks
        name,size=decls[obj]
        if name in constants:
            exported.extend([f'.BASE $C0',f'.SECTION "const_{path.stem}_{name}" SUPERFREE',name+':']+chunks+['.ENDS'])
        else: result.extend(chunks)
        chunks=[]
    for line in lines:
        if line.startswith('.RAMSECTION') and 'globram.data' in line: inram=True;result.append(line);continue
        if inram:
            if line.startswith('.ENDS'): inram=False
            m=re.match(r'(\S+)\s+dsb\s+(\d+)',line,re.I)
            if not(m and m[1] in constants):result.append(line)
            continue
        if line.startswith('.SECTION') and 'APPENDTO "glob.data"' in line: indata=True;result.append(line);continue
        if indata and line.startswith('.ENDS'):
            if obj!=len(decls):raise ValueError(f'{path}: data count {obj}/{len(decls)}')
            indata=False;result.append(line);continue
        if not indata:result.append(line);continue
        if not line.strip():continue
        m=re.match(r'\.(db|dw)\s+(.*)',line)
        if not m:raise ValueError(f'{path}: unsupported initializer {line[:80]}')
        size=1 if m[1]=='db' else 2
        values=m[2].split(',')
        for value in values:
            chunks.append('.'+m[1]+' '+value)
            consumed+=size
            if consumed==decls[obj][1]:finish();obj+=1;consumed=0
            elif consumed>decls[obj][1]:raise ValueError(f'{path}: initializer crosses object')
    path.write_text('\n'.join(result+exported)+'\n')

if __name__=='__main__':
    for arg in sys.argv[1:]:convert(Path(arg))
