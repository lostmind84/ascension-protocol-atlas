import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.Function;
import ghidra.program.model.address.Address;

public class Writers2 extends GhidraScript {
    @Override
    public void run() throws Exception {
        DecompInterface ifc = new DecompInterface();
        ifc.openProgram(currentProgram);
        for (String a : getScriptArgs()) {
            Address addr = currentProgram.getImageBase().getNewAddress(Long.parseLong(a, 16));
            Function f = getFunctionContaining(addr);
            if (f == null) { println("=== " + a + ": no function"); continue; }
            DecompileResults r = ifc.decompileFunction(f, 90, monitor);
            if (!r.decompileCompleted()) { println("=== " + a + ": decompile failed"); continue; }
            String c = r.getDecompiledFunction().getC();
            println("=== " + f.getName() + " @ " + f.getEntryPoint() + " (" + c.length() + ")");
            for (String line : c.split("\n"))
                if (line.contains("0x19c") || line.contains("0x198") || line.contains("0x2c"))
                    println("    " + line.trim());
        }
    }
}
