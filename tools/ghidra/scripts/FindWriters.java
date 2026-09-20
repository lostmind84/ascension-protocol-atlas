import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;
import java.util.*;

public class FindWriters extends GhidraScript {
    @Override
    public void run() throws Exception {
        Address singleton = currentProgram.getImageBase().getNewAddress(0x10a315d0L);
        DecompInterface ifc = new DecompInterface();
        ifc.openProgram(currentProgram);
        Set<Function> seen = new LinkedHashSet<>();
        for (Reference r : getReferencesTo(singleton)) {
            Function f = getFunctionContaining(r.getFromAddress());
            if (f != null) seen.add(f);
        }
        println("callers of the singleton getter: " + seen.size());
        int printed = 0;
        for (Function f : seen) {
            DecompileResults res = ifc.decompileFunction(f, 45, monitor);
            if (!res.decompileCompleted()) continue;
            String c = res.getDecompiledFunction().getC();
            if (!c.contains("0x198") && !c.contains("0x19c")) continue;
            println("### " + f.getName() + " @ " + f.getEntryPoint() + "  (" + c.length() + " chars)");
            if (printed++ < 4) println(c.length() > 4000 ? c.substring(0, 4000) : c);
        }
        println("functions touching the container: " + printed);
    }
}
