#!/usr/bin/env python3
"""Headless SNES cartridge smoke tests using the actual Snes9x CPU/PPU/APU."""
import ctypes as C
from pathlib import Path
import re,json,sys,hashlib
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
PAD={'B':0,'Y':1,'SELECT':2,'START':3,'UP':4,'DOWN':5,'LEFT':6,'RIGHT':7,'A':8,'X':9,'L':10,'R':11}
class Info(C.Structure):
    _fields_=[('path',C.c_char_p),('data',C.c_void_p),('size',C.c_size_t),('meta',C.c_char_p)]
class Runner:
    def __init__(self,render=True,rom_patch=None,rom_path=None):
        self.render=render
        self.frame=None;self.pixel=0;self.masks=[0,0];self.audio_peak=0;self.frames=0
        self.core=l=C.CDLL('/usr/lib/x86_64-linux-gnu/libretro/snes9x_libretro.so')
        def env(cmd,p):
            if (cmd&0xffff)==47:
                C.cast(p,C.POINTER(C.c_uint))[0]=(1 if self.render else 0)|2;return True
            if cmd==10:self.pixel=C.cast(p,C.POINTER(C.c_int))[0];return True
            if cmd==17:C.cast(p,C.POINTER(C.c_bool))[0]=False;return True
            if cmd==3:return False
            return cmd in (18,35,37)
        def video(p,w,h,pitch):
            if not p or not self.render:return
            a=np.frombuffer(C.string_at(p,pitch*h),np.uint8).reshape(h,pitch)
            if self.pixel==1:self.frame=a[:,:w*4].reshape(h,w,4)[:,:,[2,1,0]].copy()
            else:
                a=a[:,:w*2].copy().view(np.uint16).reshape(h,w).astype(np.uint32)
                if self.pixel==2:r=(a>>11)&31;g=(a>>5)&63;b=a&31;g=g*255//63
                else:r=(a>>10)&31;g=(a>>5)&31;b=a&31;g=g*255//31
                self.frame=np.stack((r*255//31,g,b*255//31),axis=2).astype(np.uint8)
        def batch(p,n):
            a=np.ctypeslib.as_array(p,shape=(n*2,)).astype(np.int32)
            if n:self.audio_peak=max(self.audio_peak,int(np.abs(a).max()))
            return n
        callbacks=[('environment',C.CFUNCTYPE(C.c_bool,C.c_uint,C.c_void_p),env),
                   ('video_refresh',C.CFUNCTYPE(None,C.c_void_p,C.c_uint,C.c_uint,C.c_size_t),video),
                   ('audio_sample',C.CFUNCTYPE(None,C.c_int16,C.c_int16),lambda a,b:None),
                   ('audio_sample_batch',C.CFUNCTYPE(C.c_size_t,C.POINTER(C.c_int16),C.c_size_t),batch),
                   ('input_poll',C.CFUNCTYPE(None),lambda:None),
                   ('input_state',C.CFUNCTYPE(C.c_int16,C.c_uint,C.c_uint,C.c_uint,C.c_uint),lambda port,dev,idx,button:int(port<2 and bool(self.masks[port]&(1<<button))))]
        self.callbacks=[]
        for name,typ,fn in callbacks:
            cb=typ(fn);self.callbacks.append(cb);f=getattr(l,'retro_set_'+name);f.argtypes=[typ];f(cb)
        l.retro_init()
        path=Path(rom_path) if rom_path is not None else ROOT/'snes/sidearms_md_snes.sfc'
        changed=[p for folder in ('src','inc') for p in (ROOT/'snes'/folder).rglob('*') if p.suffix in ('.c','.h','.asm') and p.stat().st_mtime>path.stat().st_mtime]
        if rom_path is None:assert not changed,'ROM is older than its sources; run make first'
        raw=path.read_bytes()
        if rom_patch is not None:raw=rom_patch(raw)
        self.rom=raw;self.rom_sha256=hashlib.sha256(raw).hexdigest();self.buffer=C.create_string_buffer(raw)
        info=Info(str(path).encode(),C.cast(self.buffer,C.c_void_p),len(raw),None)
        l.retro_load_game.argtypes=[C.POINTER(Info)];l.retro_load_game.restype=C.c_bool
        assert l.retro_load_game(C.byref(info)), 'ROM load failed'
        l.retro_get_memory_data.argtypes=[C.c_uint];l.retro_get_memory_data.restype=C.c_void_p
        self.ram=(C.c_uint8*131072).from_address(l.retro_get_memory_data(2))
        self.symbols={}
        for line in path.with_suffix('.sym').read_text().splitlines():
            m=re.match(r'^([0-9a-fA-F]+) (\S+)$',line)
            if m:self.symbols[m[2]]=int(m[1],16)
        a=self.symbols['native_player_layout'];off=((a>>16)&63)*65536+(a&65535)
        values=[int.from_bytes(raw[off+i:off+i+2],'little') for i in range(0,16,2)]
        self.layout=dict(zip(('player_size','x','y','invuln','lives','shots','shot_size','shot_active'),values))
    def addr(self,name):
        if name in self.symbols:return self.symbols[name]
        matches=[v for k,v in self.symbols.items() if k.endswith('_'+name)]
        if len(matches)!=1:raise KeyError((name,len(matches)))
        return matches[0]
    def read(self,name,n=2,offset=0):
        a=(self.addr(name)&0x1ffff)+offset;return int.from_bytes(bytes(self.ram[a:a+n]),'little')
    def write(self,name,v,n=2,offset=0):
        a=(self.addr(name)&0x1ffff)+offset
        self.ram[a:a+n]=v.to_bytes(n,'little')
    def run(self,n,buttons=(),port=0):
        self.masks[port]=sum(1<<PAD[b] for b in buttons)
        for _ in range(n):self.core.retro_run();self.frames+=1
    def capture(self,name):
        if not self.render:
            self.render=True;self.run(1);self.render=False
        path=ROOT/'build/qa'/f'{name}.png';path.parent.mkdir(exist_ok=True);Image.fromarray(self.frame).save(path)
    def snapshot_block(self,tag):
        self.core.retro_serialize_size.restype=C.c_size_t
        n=self.core.retro_serialize_size();buf=C.create_string_buffer(n)
        self.core.retro_serialize.argtypes=[C.c_void_p,C.c_size_t]
        assert self.core.retro_serialize(buf,n),'Snes9x snapshot failed'
        raw=buf.raw;p=raw.index(b'\n')+1
        while p+11<len(raw):
            name=raw[p:p+3];size=int(raw[p+4:p+10]);p+=11
            if name==tag:return raw[p:p+size]
            p+=size
        raise KeyError(tag)
    def logic(self,n,buttons=(),port=0):
        start=self.read('frame_counter',4)
        if start>0x1000000:start=0
        for _ in range(max(12000,n*100+1000)):
            self.run(1,buttons,port)
            now=self.read('frame_counter',4)
            if now<0x1000000 and now-start>=n:return
        raise AssertionError('Main loop stalled')
    def press(self,button,port=0):
        self.logic(2,[button],port);self.logic(2,[],port)

if __name__=='__main__':
    r=Runner();r.logic(5);r.capture('boot'); print('boot',r.read('frame_counter',4),r.read('flow_state'),flush=True)
    r.press('START');r.logic(30);r.capture('arcade');print('arcade',r.read('frame_counter',4),r.read('flow_state'),flush=True)
    r.press('START');r.logic(10);r.press('START');r.logic(600);r.capture('game');print('game',r.read('frame_counter',4),r.read('flow_state'),r.audio_peak,flush=True)
    r.logic(120,['B']);r.capture('shooting');print('shoot',r.read('frame_counter',4),r.read('native_dma_overflow'),flush=True)
    result={'rom_sha256':r.rom_sha256,'emulated_frames':r.frames,'game_frames':r.read('frame_counter',4),'flow_state':r.read('flow_state'),'audio_peak':r.audio_peak,'audio_timeouts':r.read('audio_flush_timeouts'),'dma_overflow':r.read('native_dma_overflow')}
    (ROOT/'build/qa/smoke.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['game_frames']>0,'Main loop did not advance'
    assert result['dma_overflow']==0,'Video queue overflow'
    assert result['flow_state']==7,'Arcade start did not reach active gameplay'
    assert result['audio_peak']>0,'Audio remained silent'
    assert result['audio_timeouts']==0,'SPC700 command handshake timed out'
    print(result)
