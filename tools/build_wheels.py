"""Prepare stationary wheel arenas: resident patterns and three 32-column maps."""
import re,struct
from pathlib import Path

def build_wheels(up,planar):
    source=(up/'src/gen/boss_data.c').read_text();gen=up/'res/generated'
    def array(name):
        m=re.search(r'\b'+name+r'\[[^\]]*\][^=]*=\s*\{(.*?)\};',source,re.S)
        if not m:raise ValueError(name)
        return [int(v,0) for v in re.findall(r'0x[\da-fA-F]+|\d+',m[1])]
    def words(name):return list(struct.unpack('>'+str((gen/(name+'.bin')).stat().st_size//2)+'H',(gen/(name+'.bin')).read_bytes()))
    blobs={};metadata=[]
    for n,home,z,cx,cy in ((0,0,1,864,272),(0,1,1,864,272),(1,0,8,2912,2320),(1,1,8,2912,2320),(2,0,20,2912,2576)):
        stem=f'wheel{n}'+('h' if home else '');maps=array(stem+'_maps')
        m=re.search(r'const BgFrames '+stem+r'_frames\s*=\s*\{\s*([\d, ]+),',source)
        vals=[int(v) for v in re.findall(r'\d+',m[1])];_,fx,fy,w,h,nf=vals[:6]
        meta_count=len(words(f'zone{z}_attr'))//16
        base_tiles=(gen/f'zone{z}_tiles.bin').read_bytes();base_attr=words(f'zone{z}_attr')
        extra_tiles=bytes(array(stem+'_tiles')) if re.search(r'\b'+stem+r'_tiles\[',source) else b''
        extra_attr=array(stem+'_tmpl') if extra_tiles else []
        keys=sorted({v&4095 for v in maps if v!=65535})
        assert len(keys)<=47,(stem,len(keys))
        slots={key:i for i,key in enumerate(keys)};tiles=bytearray()
        for key in keys:
            raw=base_tiles[key*512:(key+1)*512] if key<meta_count else extra_tiles[(key-meta_count)*512:(key-meta_count+1)*512]
            assert len(raw)==512,(stem,key)
            tiles+=planar(raw)
        native=[]
        for frame in range(3):
            result=[0]*1024
            for y in range(28):
                for x in range(32):
                    wx=(cx+32)//8+x;wy=cy//8+y;mx,my=wx//4,wy//4
                    assert fx<=mx<fx+w and fy<=my<fy+h,(stem,mx,my)
                    e=maps[(frame*h+my-fy)*w+mx-fx];key=e&4095
                    if e==65535:continue
                    sx,sy=wx&3,wy&3;hf=bool(e&0x4000);vf=bool(e&0x8000)
                    t=(3-sy if vf else sy)*4+(3-sx if hf else sx)
                    attr=base_attr[key*16+t] if key<meta_count else extra_attr[(key-meta_count)*16+t]
                    if attr:result[y*32+x]=16+slots[key]*16+t+(((attr>>13)&1)<<10)+0x3000+(e&0xc000)
            native+=result
        name='native_'+stem
        blobs[name+'_keys']=struct.pack('<'+str(len(keys))+'H',*keys)
        blobs[name+'_tiles']=bytes(tiles)
        blobs[name+'_maps']=struct.pack('<3072H',*native)
        metadata.append((n,home,len(keys),cx,cy,name))
    return blobs,metadata
