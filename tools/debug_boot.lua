local n=0
local f=assert(io.open(os.getenv('SIDEARMS_DEBUG_OUT') or '/tmp/sidearms-md-boot.txt','w'))
emu.addEventCallback(function()
 n=n+1
 if n==60 or n==120 then
  f:write('FRAME '..n..'\n')
  for k,v in pairs(emu.getState()) do
   if type(v)~='table' then f:write(tostring(k)..'='..tostring(v)..'\n') end
  end
  f:flush()
 end
 if n==120 then f:close();emu.stop(0) end
end,emu.eventType.endFrame)
