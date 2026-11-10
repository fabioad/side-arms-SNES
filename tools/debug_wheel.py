#!/usr/bin/env python3
from pathlib import Path
import re,subprocess,json,sys
ROOT=Path(__file__).resolve().parents[1]
syms={}
for line in (ROOT/'snes/sidearms_md_snes.sym').read_text().splitlines():
    m=re.match(r'^([0-9a-fA-F]+) (\S+)$',line)
    if m:syms[m[2]]=int(m[1],16)
a={k:syms[k]&0x1ffff for k in ('frame_counter','flow_state','credits','players','dbg_warp','native_phase','audio_step','boss_dbg_autohit')}
rom=(ROOT/'snes/sidearms_md_snes.sfc').read_bytes();meta=syms['native_player_layout'];off=((meta>>16)&63)*65536+(meta&65535)
a['invuln']=int.from_bytes(rom[off+6:off+8],'little')
a['lives']=int.from_bytes(rom[off+8:off+10],'little')
lua='local A='+ '{'+','.join(k+'='+str(v) for k,v in a.items())+'}\n'
lua+='local out='+json.dumps(str(ROOT/'build'))+'\n'
lua+=r'''
local ram=emu.memType.snesWorkRam
local function r16(a) return emu.read(a,ram)+256*emu.read(a+1,ram) end
local function w16(a,v) emu.write(a,v&255,ram);emu.write(a+1,(v>>8)&255,ram) end
local seq={'start','','start','','start','','b','','b','','b',''}
local step=0
local next=0
local last=-1
local idle=0
local n=0
local warped=false
local played=nil
emu.addEventCallback(function()
 local pad={}
 if step>=1 and step<=#seq and seq[step]~='' then pad[seq[step]]=true end
 emu.setInput(pad,0)
 if warped then emu.write(A.players+A.invuln,255,ram) end
end,emu.eventType.inputPolled)
emu.addEventCallback(function()
 n=n+1
 local fc=r16(A.frame_counter)
 if step==0 and fc>=5 and fc<3000 then step=1;next=fc+2 end
 if step>0 and step<=#seq and fc>=next then step=step+1;next=fc+2 end
 if r16(A.flow_state)==7 and not played then played=fc end
 if played and fc-played>100 and not warped then w16(A.dbg_warp,0x102);warped=true end
 if fc==last then idle=idle+1 else last=fc;idle=0 end
 if (idle>180 and fc>=5 and fc<3000) or (warped and idle>180) or n==18000 then
  local f=assert(io.open(out..'/wheel-cpu.txt','w'))
  f:write('frame='..n..' game='..fc..' phase='..emu.read(A.native_phase,ram)..' audio='..r16(A.audio_step)..'\n')
  for k,v in pairs(emu.getState()) do if string.match(k,'^cpu%.') or (string.match(k,'^spc%.') and not string.find(k,'dsp')) then f:write(tostring(k)..'='..tostring(v)..'\n') end end
  f:close()
  local p=assert(io.open(out..'/qa/wheel-debug.png','wb'));p:write(emu.takeScreenshot());p:close()
  emu.stop(0)
 end
end,emu.eventType.endFrame)
'''
if len(sys.argv)>1:
    if sys.argv[1]=='campaign':
        lua=lua.replace("w16(A.dbg_warp,0x102);warped=true", "warped=true")
        lua=lua.replace('emu.write(A.players+A.invuln,255,ram)', 'emu.write(A.players+A.invuln,255,ram);emu.write(A.players+A.lives,9,ram);emu.write(A.boss_dbg_autohit,1,ram)')
        lua=lua.replace('n==18000','n==100000')
    else:lua=lua.replace('0x102',str(int(sys.argv[1],0)))
(ROOT/'build/debug-wheel.lua').write_text(lua)
with (ROOT/'build/mesen-wheel.log').open('w') as f:
    subprocess.run(['mesen','--testRunner',str(ROOT/'snes/sidearms_md_snes.sfc'),str(ROOT/'build/debug-wheel.lua')],stdout=f,stderr=subprocess.STDOUT,timeout=120,check=True)
print((ROOT/'build/wheel-cpu.txt').read_text())
