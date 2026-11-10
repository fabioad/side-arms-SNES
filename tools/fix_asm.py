#!/usr/bin/env python3
"""Keep 816-tcc's byte data lines within WLA-DX's input buffer."""
import sys,re
from pathlib import Path
p=Path(sys.argv[1]); result=[]; joined=[]
for line in p.read_text().splitlines():
    if joined and re.fullmatch(r'[0-9a-fA-F$,]+',line) and joined[-1].startswith('.db '): joined[-1]+=line
    else: joined.append(line)
for line in joined:
    if line.startswith('.SECTION "SOUNDBANK') and 'KEEP' not in line:
        line=line.split(';')[0].rstrip()+' KEEP'
    if line.startswith('.RAMSECTION ".bss"'):
        line='.RAMSECTION "port_bss_{WLA_FILENAME}" APPENDTO "port_bss"'
    if line.startswith('.SECTION ".rodata"') and 'SEMIFREE' in line:
        line='.BASE $C0\n.SECTION ".rodata" SUPERFREE'+(' KEEP' if p.stem=='layout' else '')
    if line.startswith('.db ') and len(line)>1000:
        values=line[4:].split(',')
        result.extend('.db '+','.join(values[i:i+32]) for i in range(0,len(values),32))
    else: result.append(line)
s='\n'.join(result)+'\n'
refs=set(re.findall(r'(__[^\s()#+,;]+_locals)\b',s))
defs=set(re.findall(r'\.define\s+(\S+_locals)\b',s))
s='\n'.join('.define '+name+' 0' for name in sorted(refs-defs))+'\n'+s
p.write_text(s)
