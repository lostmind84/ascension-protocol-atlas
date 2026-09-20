import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;

public class Decomp extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        DecompInterface ifc = new DecompInterface();
        ifc.openProgram(currentProgram);
        for (String a : args) {
            Address addr = currentProgram.getImageBase().getNewAddress(Long.parseLong(a, 16));
            Function f = getFunctionContaining(addr);
            if (f == null) { println("=== " + a + ": no function"); continue; }
            println("=== " + a + "  " + f.getName() + " @ " + f.getEntryPoint());
            DecompileResults r = ifc.decompileFunction(f, 60, monitor);
            println(r.decompileCompleted() ? r.getDecompiledFunction().getC() : "decompile failed");
        }
    }
}
