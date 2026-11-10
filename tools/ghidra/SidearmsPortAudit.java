// @category SideArms
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import java.io.*;

/** Export real Z80 disassembly and decompilation of routines used by the MD port. */
public class SidearmsPortAudit extends GhidraScript {
    public void run() throws Exception {
        String[] args = getScriptArgs();
        File out = new File(args[0]); out.mkdirs();
        boolean sound = currentProgram.getName().equals("sound.bin");
        int[] entries = sound
            ? new int[]{0x0000,0x0038,0x013b,0x0141,0x015c,0x01f2,0x02d3,0x031b}
            : new int[]{0x0000,0x0038,0x0627,0x0715,0x1fc9,0x2001,0x2044,0x2500,0x8051,0x8057,0x809c,0x80ca,0x8194};
        for (int a : entries) {
            disassemble(toAddr(a));
            if (getFunctionAt(toAddr(a)) == null) createFunction(toAddr(a), "arcade_" + Integer.toHexString(a));
        }
        analyzeAll(currentProgram);
        DecompInterface dec = new DecompInterface(); dec.openProgram(currentProgram);
        try (PrintWriter w = new PrintWriter(new File(out, currentProgram.getName()+".txt"))) {
            w.println("Program: " + currentProgram.getName());
            w.println("Language: " + currentProgram.getLanguageID());
            if (sound) {
                w.println("\nOriginal sound-command dispatch ($00BB, 64 little-endian pointers):");
                for (int cmd=0; cmd<64; cmd++)
                    w.printf("command $%02X -> $%04X%n",cmd,getShort(toAddr(0x00bb+cmd*2)) & 0xffff);
            }
            for (int a : entries) {
                w.printf("\n=== $%04X ===\n", a);
                Instruction ins = getInstructionAt(toAddr(a));
                for(int n=0; ins != null && n<40; n++, ins=ins.getNext()) w.println(ins.getAddress()+"  "+ins);
                Function f = getFunctionAt(toAddr(a));
                if(f != null) {
                    DecompileResults r = dec.decompileFunction(f, 30, monitor);
                    if(r.decompileCompleted()) w.println(r.getDecompiledFunction().getC());
                    else w.println(r.getErrorMessage());
                }
            }
        } finally { dec.dispose(); }
    }
}
