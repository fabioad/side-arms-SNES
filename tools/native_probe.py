"""Run small native-CPU test trampolines without modifying the production ROM."""
import ctypes as C,re
from test_snes import Runner,ROOT

def symbols(rom_path=None):
    from pathlib import Path
    path=Path(rom_path).with_suffix('.sym') if rom_path else ROOT/'snes/sidearms_md_snes.sym'
    return {m[2]:int(m[1],16) for line in path.read_text().splitlines()
            if (m:=re.match(r'([0-9a-fA-F]+) (\S+)$',line))}
def le(n,size=2):return n.to_bytes(size,'little')
def enemy_call(address,big,enemy):
    return (bytes.fromhex('18 fb c2 30 08')+b'\xf4'+le(big)+b'\xf4'+le(enemy>>16)+b'\xf4'+le(enemy&65535)+
            b'\x22'+le(address,3)+bytes.fromhex('c2 30 3b 18 69 06 00 1b a9 5a a5 8f 08 ff 7f 28 db'))
class Probe:
    def __init__(self,programs,rom_path=None):
        def patch(raw):
            raw=bytearray(raw)
            for i,code in enumerate(programs):
                assert len(code)<256
                off=55*65536+i*256
                assert len(set(raw[off:off+len(code)]))==1,'Probe bank occupied'
                raw[off:off+len(code)]=code
            return bytes(raw)
        self.r=Runner(False,rom_patch=patch,rom_path=rom_path);self.r.logic(5);l=self.r.core
        l.retro_serialize_size.restype=C.c_size_t;self.size=l.retro_serialize_size()
        buf=C.create_string_buffer(self.size);l.retro_serialize.argtypes=[C.c_void_p,C.c_size_t]
        assert l.retro_serialize(buf,self.size)
        base=bytearray(buf.raw);p=base.index(b'\n')+1
        while base[p:p+3]!=b'REG':p+=11+int(base[p+4:p+10])
        p+=11;base[p]=0xf7;base[p+8:p+10]=(0x1ff0).to_bytes(2,'big');base[p+6:p+8]=b'\0\0'
        self.states=[]
        for i in range(len(programs)):
            base[p+14:p+16]=(i*256).to_bytes(2,'big');self.states.append(C.create_string_buffer(bytes(base)))
        l.retro_unserialize.argtypes=[C.c_void_p,C.c_size_t];l.retro_unserialize.restype=C.c_bool
    def restore(self,i):
        assert self.r.core.retro_unserialize(self.states[i],self.size)
        self.r.ram[0x1ff08:0x1ff0a]=[0,0]
    def run(self):
        self.r.run(1)
        assert bytes(self.r.ram[0x1ff08:0x1ff0a])==b'\x5a\xa5','Probe failed to return'
