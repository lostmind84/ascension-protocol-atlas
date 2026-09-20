import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;

public class DecompAt extends GhidraScript {
    @Override
    public void run() throws Exception {
        DecompInterface ifc = new DecompInterface();
        ifc.openProgram(currentProgram);
        for (String a : getScriptArgs()) {
            Address addr = currentProgram.getImageBase().getNewAddress(Long.parseLong(a, 16));
            Function f = getFunctionAt(addr);
            if (f == null) f = getFunctionContaining(addr);
            if (f == null || !f.getEntryPoint().equals(addr)) {
                disassemble(addr);
                f = createFunction(addr, "sub_" + a);
            }
            if (f == null) { println("=== " + a + ": could not create a function"); continue; }
            println("=== " + a + "  " + f.getName() + " @ " + f.getEntryPoint());
            DecompileResults r = ifc.decompileFunction(f, 60, monitor);
            println(r.decompileCompleted() ? r.getDecompiledFunction().getC() : "decompile failed");
        }
    }
}
