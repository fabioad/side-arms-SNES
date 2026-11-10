local ram=emu.memType.snesWorkRam
local out=assert(os.getenv("SA1_PROBE_RESULT"))
local frames=0
local function r16(addr)
    return emu.read(addr,ram)+256*emu.read(addr+1,ram)
end
emu.addEventCallback(function()
    frames=frames+1
    local status=emu.read(0x2000,ram)
    if status==0xa5 or status==0xee or frames==120 then
        local file=assert(io.open(out,"w"))
        file:write("status=",status,"\nframes=",frames,"\n")
        for i=0,5 do
            file:write("v",i,"=",r16(0x2010+i*2),"\nf",i,"=",r16(0x2040+i*2),"\n")
        end
        for i=0,5 do
            file:write("second_v",i,"=",r16(0x2060+i*2),"\nsecond_f",i,"=",r16(0x2070+i*2),"\n")
        end
        for i=0,575 do
            file:write(string.format("%02x",emu.read(0x2100+i,ram)))
        end
        file:write("\n")
        for i=0,575 do
            file:write(string.format("%02x",emu.read(0x2340+i,ram)))
        end
        file:write("\n")
        for i=0,575 do
            file:write(string.format("%02x",emu.read(0x27c0+i,ram)))
        end
        file:write("\n")
        for i=0,575 do
            file:write(string.format("%02x",emu.read(0x2580+i,ram)))
        end
        file:write("\n")
        file:close()
        emu.stop(status==0xa5 and 0 or 1)
    end
end,emu.eventType.endFrame)
