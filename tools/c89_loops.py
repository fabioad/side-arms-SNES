"""Preserve loop-local scope when lowering C99 for declarations for 816-tcc."""
import re

def lower(source):
    # Ignore comments and strings while retaining character offsets.
    clean=re.sub(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'',lambda m:' '*len(m[0]),source,flags=re.S)
    tokens=list(re.finditer(r'[A-Za-z_]\w*|[^\s]',clean))
    vals=[m[0] for m in tokens]
    pairs={}; stack=[]
    for i,v in enumerate(vals):
        if v in ('(','{','['): stack.append(i)
        elif v in (')','}',']'):
            if stack: pairs[stack.pop()]=i
    def end(i):
        v=vals[i]
        if v=='{': return pairs[i]+1
        if v in ('for','while','switch','if'):
            j=end(pairs[i+1]+1)
            if v=='if' and j<len(vals) and vals[j]=='else': j=end(j+1)
            return j
        if v=='do':
            j=end(i+1)
            return pairs[j+1]+2
        while i<len(vals):
            if vals[i]==';': return i+1
            if vals[i] in ('(','[','{'): i=pairs[i]+1
            else: i+=1
        raise ValueError('unterminated C statement')
    edits=[]
    for i,v in enumerate(vals):
        if v!='for' or vals[i+1]!='(' or vals[i+2] not in ('u8','u16','u32','s8','s16','s32','int','unsigned'): continue
        typ=vals[i+2]; name=vals[i+3]
        if vals[i+4]!='=': raise ValueError('unexpected loop declaration')
        j=end(i)
        edits.extend([(tokens[i].start(),tokens[i].start(),'{ '+typ+' '+name+'; '),
                      (tokens[i+2].start(),tokens[i+2].end(),''),
                      (tokens[j-1].end(),tokens[j-1].end(),' }')])
    for a,b,s in sorted(edits,reverse=True): source=source[:a]+s+source[b:]
    # 816-tcc miscompiles a for-loop with an empty condition and an increment
    # into a self-branch before its body. An explicit true condition is equivalent.
    source=re.sub(r'\bfor\s*\(([^;]*);\s*;',r'for (\1; 1;',source)
    return source

if __name__=='__main__':
    import sys
    from pathlib import Path
    for name in sys.argv[1:]:
        p=Path(name); p.write_text(lower(p.read_text()))
