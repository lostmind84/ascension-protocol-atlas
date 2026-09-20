// Decompile every function listed in a "<hex VA> <opcode>" file into <outdir>/<opcode>.c, one
// file per line, so the C can be searched and parsed without re-running Ghidra.
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import java.io.*;

public class DumpC extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        BufferedReader in = new BufferedReader(new FileReader(args[0]));
        File dir = new File(args[1]);
        dir.mkdirs();
        DecompInterface ifc = new DecompInterface();
        ifc.openProgram(currentProgram);
        String line; int n = 0;
        while ((line = in.readLine()) != null) {
            String[] parts = line.trim().split("\\s+");
            if (parts.length < 2) continue;
            Address addr = currentProgram.getImageBase().getNewAddress(Long.parseLong(parts[0], 16));
            Function f = getFunctionContaining(addr);
            if (f == null) {                 // Ghidra defines no function at some registered handlers: create one
                disassemble(addr);
                f = createFunction(addr, "handler_" + parts[1]);
            }
            PrintWriter out = new PrintWriter(new FileWriter(new File(dir, parts[1] + ".c")));
            out.println("// " + parts[1] + " handler at " + parts[0] + (f == null ? " (no function)" : " " + f.getName()));
            if (f != null) {
                DecompileResults r = ifc.decompileFunction(f, 45, monitor);
                out.println(r.decompileCompleted() ? r.getDecompiledFunction().getC() : "// decompile failed");
            }
            out.close();
            if (++n % 100 == 0) println("decompiled " + n);
        }
        println("done: " + n);
    }
}
