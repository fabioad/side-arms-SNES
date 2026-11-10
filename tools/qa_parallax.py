#!/usr/bin/env python3
"""Exercise the real native parallax and compare its committed maps to MD pixels."""
import hashlib,json,struct
import numpy as np
from native_probe import Probe,symbols,le
from test_snes import ROOT
s=symbols()
def call(name,*args):
    sizes=([4] if name=='bg_frames_begin' else [1]*len(args) if name in ('video_set_parallax','video_set_layers','bgSetDisable') else [2]*len(args))
    b=b''
    for v,n in reversed(list(zip(args,sizes))):
        if n==1:b+=bytes.fromhex('e2 20 a9')+bytes([v])+bytes.fromhex('48 c2 20')
        else:
            if n==4:b+=b'\xf4'+le(v>>16)
            b+=b'\xf4'+le(v&65535)
    b+=b'\x22'+le(s[name],3)
    if args:b+=bytes.fromhex('3b 18 69')+le(sum(sizes))+b'\x1b'
    return b
def frame():return call('video_frame')+call('native_prepare_flush')+call('native_wait_vblank')+call('native_flush')
cases=[('rows',0,600,16,True,None),('columns3',3,96,1001,True,None),
       ('columns6',12,480,2503,True,None),('cave',10,2400,2064,True,None),
       ('plain',0,600,16,False,None),('rows-cut',0,3000,16,True,(600,16)),
       ('columns-to-rows',3,96,783,True,(96,1001)),
       ('rows-to-columns',3,96,1001,True,(96,783)),
       ('cave-to-rows',10,2400,2063,True,(2400,2064)),
       ('columns-off',3,96,1001,False,(96,1001)),
       ('wheel0-home',1,864,272,True,None),('wheel1-home',8,2912,2320,True,None)]
programs=[]
for name,z,x,y,on,initial in cases:
    b=bytes.fromhex('18 fb c2 30 08')+call('video_set_parallax',True if initial else on)+call('bg_set_zone',z)+call('video_set_layers',1,1)
    if initial:b+=call('video_set_camera',*initial)+frame()+call('video_set_parallax',on)
    if name.startswith('wheel'):
        addr=next(v for k,v in s.items() if k.endswith('_'+name[:6]+'h_frames'))
        b+=call('bg_frames_begin',addr)+call('bg_frames_show',1)
    b+=call('video_set_camera',x,y)+frame()+call('bgSetDisable',0)+call('bgSetDisable',1)
    b+=bytes.fromhex('c2 30 a9 5a a5 8f 08 ff 7f 28 cb 80 fd');programs.append(b)
p=Probe(programs);r=p.r;r.render=True;out=[]
speeds=(2,4,8,12);cols=[3,1,2,1,3,1,3,2,1,0,2,0,2,0,3,1,0,2,0,3]
rows=[1,3,1,2,2,0,1,3,3,2,3,1,1,1,0,2,3,2,0,0,0,2,1,2,3,2,1,3,3,0,0,0]
# Independent packed-MD pixel reader, independent of native phase tables.
raw=(ROOT/'res/generated/star_tiles.bin').read_bytes()
mdmap=struct.unpack('>2048H',(ROOT/'res/generated/star_map.bin').read_bytes())
palettes=((1,2,3),(1,2,17),(1,3,18),(2,17,18),(17,18,0),(5,6,0))
def mdpixel(x,y):
    e=mdmap[((y&255)//8)*64+(x&511)//8];b=raw[(e&2047)*32+(y&7)*4+(x&7)//2];pen=(b>>(0 if x&1 else 4))&15
    return pen+((e>>13)&1)*16 if pen else 0
def decoded(v,e,x,y):
    t=(e&1023)*16;pen=sum(((v[0x6000+t+y*2+b]>>(7-x))&1)<<b for b in range(2))
    return palettes[(e>>10)&7][pen-1] if pen else 0
for i,(name,z,x,y,on,initial) in enumerate(cases):
    p.restore(i)
    for _ in range(100):
        r.run(1)
        if bytes(r.ram[0x1ff08:0x1ff0a])==b'\x5a\xa5':break
    else:raise AssertionError(('Native parallax probe stalled',name))
    v=r.snapshot_block(b'VRA');mode=r.read('par_dbg_mode',1)
    expected_mode=0 if not on else 3 if z==10 and y==2064 and 1569<=x<=3679 else 2 if (x in (96,480,864) and ((z==3 and y>=784) or (z==12 and y>=2064))) else 1
    assert mode==expected_mode,(name,mode,expected_mode)
    xoff=[0]*4;yoff=[0]*4;voff=0
    if initial and max(abs(x-initial[0]),abs(y-initial[1]))>16:
        xoff=[initial[0]*sp//16-x*sp//16 for sp in speeds]
        yoff=[initial[1]*sp//16-y*sp//16 for sp in speeds]
        voff=((initial[1]//2-y//2)+4)&~7
    vs=y//2+voff
    if name.startswith('wheel'):
        metas=len((ROOT/f'snes/res/zone{z}_attr.bin').read_bytes())//32
        addr=next(v for k,v in s.items() if k.startswith('tccs_') and k.endswith('_'+name[:6]+'h_tiles'))&0x3fffff
        checked=0
        for slot in range(47):
            key=r.read('native_bg_keys',2,slot*2)
            if key==65535 or key<metas:continue
            off=addr+(key-metas)*512
            assert v[0x200+slot*512:0x200+(slot+1)*512]==r.rom[off:off+512],('Wrong Home wheel extra tiles',name,key)
            checked+=1
        assert checked>0,('No Home wheel extra tiles checked',name)
    if mode==1:
        a=r.addr('par_hdma_active')&0x1ffff;data=bytes(r.ram[a:a+100]);line=0;j=0
        while data[j]:
            n=data[j];offset=int.from_bytes(data[j+1:j+3],'little');j+=3
            for yy in range(line,line+n):assert offset==((x*speeds[rows[((yy+vs)>>3)&31]]//16)+xoff[rows[((yy+vs)>>3)&31]]+32)&65535
            line+=n
        assert line==224
    if mode==2:
        entries=struct.unpack('<1024H',v[0xf000:0xf800])
        for yy in range(224):
            for xx in range(256):
                e=entries[(yy//8)*32+xx//8];actual=decoded(v,e,xx&7,yy&7)
                srcx=xx+32;layer=cols[srcx//16];expected=mdpixel(srcx,yy+y*speeds[layer]//16+yoff[layer])
                assert actual==expected,(name,xx,yy,actual,expected)
    if mode==3:
        entries=struct.unpack('<2048H',v[0xf000:0x10000])
        assert entries[0]==5<<10 and entries[33]==5<<10|5
        far=(ROOT/'snes/res/native_far_tiles.bin').read_bytes();assert v[0x6000:0x6100]==far
    if mode==0:assert v[0xf000:0x10000]==(ROOT/'snes/res/snes_star_map.bin').read_bytes()
    for pal,colors in enumerate(palettes):
        for pen,color in enumerate(colors,1):
            if color:assert r.read('palram',2,(pal*4+pen)*2)==r.read('palram',2,(64+color)*2),('Star/far palette mismatch',name,pal,pen)
    assert r.read('native_dma_overflow')==0 and r.read('native_dma_late')==0
    r.run(2);r.capture('parallax-'+name)
    if mode in (1,2):
        expected=np.zeros((224,256),bool)
        for yy in range(224):
            for xx in range(256):
                if mode==1:
                    layer=rows[((yy+vs)//8)&31]
                    sx=xx+x*speeds[layer]//16+xoff[layer]+32;sy=yy+vs
                else:
                    sx=xx+32;layer=cols[sx//16];sy=yy+y*speeds[layer]//16+yoff[layer]
                expected[yy,xx]=bool(mdpixel(sx,sy))
        assert np.array_equal(r.frame.max(axis=2)>0,expected),('Rendered stars differ from MD pixel positions',name)
    if mode==3:
        source=(ROOT/'res/generated/zone10_far_tiles.bin').read_bytes()
        expected_pens=np.zeros((224,256),np.uint8)
        off=(min(x,3360)-1888)//2 if x>=1888 else 0
        for yy in range(224):
            for xx in range(256):
                sx=(xx+x-off+32)&31;sy=(yy+y)&31;tile=(sy//8)*4+sx//8
                packed=source[tile*32+(sy&7)*4+(sx&7)//2]
                expected_pens[yy,xx]=(packed>>(0 if sx&1 else 4))&15
        colors=[np.unique(r.frame[expected_pens==pen],axis=0) for pen in (5,6)]
        assert all(len(c)==1 for c in colors) and not np.array_equal(*colors),'Rendered cave texture differs from MD'
    out.append({'case':name,'mode':mode,'rendered_stars_match_md':True if mode in (1,2) else None,'passed':True})
result={'rom_sha256':hashlib.sha256((ROOT/'snes/sidearms_md_snes.sfc').read_bytes()).hexdigest(),'qa_native_trampoline':True,'cases':out,'passed':True}
(ROOT/'build/qa/parallax.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
