#!/usr/bin/env python3
"""Measure inclusive function time using Mesen's master clock, not video sampling."""
import os,re,json,hashlib,subprocess,argparse
from pathlib import Path
from native_probe import symbols
from test_snes import ROOT
p=argparse.ArgumentParser();p.add_argument('--section',type=int,default=6);p.add_argument('--frames',type=int,default=900);a=p.parse_args();s=symbols()
entries={};ends={}
for line in (ROOT/'snes/sidearms_md_snes.symfull').read_text().splitlines():
 m=re.match(r'([0-9a-fA-F]+) SECTION(START|END)_(.*)',line)
 if m:(entries if m[2]=='START' else ends)[m[3]]=int(m[1],16)
functions=['game_update','game_draw','video_frame','players_update','enemies_update','bosses_update','players_draw','enemies_draw','bosses_draw','hud_panel','bg_update','par_native_frame','native_prepare_flush','native_flush','native_audio_frame','tccs_src/parallax.asm_columns','tccs_src/logic/flow_game.asm_game_panel','tccs_src/logic/flow_game.asm_players_flow']
functions += ['native_enemy_update_slow','native_enemy_show','native_bg_slot','tccs_src/logic/enemies.asm_step_to','tccs_src/logic/enemies.asm_choose_target','tccs_src/logic/enemies.asm_update_all','tccs_src/background.asm_acquire','tccs_src/background.asm_render','tccs_src/background.asm_render_cell']
for file in (ROOT/'src').glob('enemy_*.c'):
    source=file.read_text()
    for static,name in re.findall(r'^(static )?(?:void|bool|u8|u16|s16) (\w+)\(',source,re.M):
        functions.append('tccs_src/logic/'+file.stem+'.asm_'+name if static else name)
functions=list(dict.fromkeys(functions))
groups=[]
for fn in functions:
 if fn not in s:continue
 start=s[fn];name=next((k for k,v in entries.items() if v==start),None)
 if name and name in ends:groups.append((fn,start,ends[name]-1))
result=ROOT/f'build/qa/mesen-section-{a.section}.txt';script=ROOT/'build/profile_mesen.lua'
lua='''local ram=emu.memType.snesWorkRam
local n,warpFrame,startFrame=0,nil,nil
local measuring=false
local sums,calls,maxima,opened={},{},{},{}
local function byte(a) return emu.read(a,ram) end
local function clock() return emu.getState()["masterClock"] end
local down=false
'''
for fn,start,end in groups:
 name=json.dumps(fn);lua+=f'''emu.addMemoryCallback(function(addr,op)
 if not measuring then return end
 if addr=={start} then opened[{name}]=clock()
 elseif op==0x6b and opened[{name}] then
  local dt=clock()-opened[{name}];opened[{name}]=nil
  sums[{name}]=(sums[{name}] or 0)+dt;calls[{name}]=(calls[{name}] or 0)+1
  maxima[{name}]=math.max(maxima[{name}] or 0,dt)
 end
end,emu.callbackType.exec,{start},{end},emu.cpuType.snes)
'''
lua+=f'''emu.addEventCallback(function()
 local input={{up=false,down=false,left=false,right=false,a=false,b=false,x=false,y=false,l=false,r=false,start=false,select=false}}
 input.down=down and n>=300 and n<320
 input.start=(n>=340 and n<360) or (n>=400 and n<420)
 input.b=(n>=460 and n<480) or (n>=500 and n<520) or (n>=540 and n<560)
 emu.setInput(input,0)
end,emu.eventType.inputPolled)
emu.addEventCallback(function()
 n=n+1
 if n==300 then down=byte({s['game_cfg']&0x1ffff})==0 end
 local flow=byte({s['flow_state']&0x1ffff})
 if flow==7 then emu.write({(s['players']&0x1ffff)+23},255,ram) end
 if n>1100 and flow==7 and byte({s['players']&0x1ffff})==1 and not warpFrame then
  emu.write({s['dbg_warp']&0x1ffff},{a.section},ram);emu.write({(s['dbg_warp']&0x1ffff)+1},0,ram);warpFrame=n
 end
 if warpFrame and n==warpFrame+300 then startFrame=n;measuring=true end
 if (startFrame and n>=startFrame+{a.frames}) or n>=6000 then
  measuring=false
  local f=assert(io.open({json.dumps(str(result))},"w"))
  f:write("frames=",n," flow=",flow," warp=",warpFrame or -1," start=",startFrame or -1,"\\n")
  for fn,total in pairs(sums) do f:write(fn,"\\t",total,"\\t",calls[fn],"\\t",maxima[fn],"\\n") end
  f:close();emu.stop(startFrame and 0 or 1)
 end
end,emu.eventType.endFrame)
'''
script.write_text(lua)
r=subprocess.run(['mesen','--testRunner',str(ROOT/'snes/sidearms_md_snes.sfc'),str(script)],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=120)
(ROOT/'build/mesen-profile.log').write_text(r.stdout);print('exit',r.returncode);print(result.read_text() if result.exists() else r.stdout[-2000:]);assert r.returncode==0
