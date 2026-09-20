import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;
import java.util.*;

public class Refs extends GhidraScript {
    @Override
    public void run() throws Exception {
        for (String a : getScriptArgs()) {
            Address addr = currentProgram.getImageBase().getNewAddress(Long.parseLong(a, 16));
            println("=== refs to " + a);
            Set<String> seen = new LinkedHashSet<>();
            for (Reference r : getReferencesTo(addr)) {
                Function f = getFunctionContaining(r.getFromAddress());
                seen.add(r.getReferenceType() + " from " + r.getFromAddress()
                        + (f == null ? " (no function)" : " in " + f.getEntryPoint()));
            }
            for (String s : seen) println("  " + s);
            println("  total: " + seen.size());
        }
    }
}
