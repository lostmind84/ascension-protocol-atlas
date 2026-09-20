import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;
import java.util.*;

public class Callers extends GhidraScript {
    @Override
    public void run() throws Exception {
        for (String a : getScriptArgs()) {
            Address addr = currentProgram.getImageBase().getNewAddress(Long.parseLong(a, 16));
            Function target = getFunctionContaining(addr);
            println("=== callers of " + a + (target == null ? "" : " (" + target.getName() + ")"));
            Set<String> seen = new LinkedHashSet<>();
            for (Reference r : getReferencesTo(target == null ? addr : target.getEntryPoint())) {
                Function f = getFunctionContaining(r.getFromAddress());
                seen.add(f == null ? r.getFromAddress() + " (no function)"
                                   : f.getName() + " @ " + f.getEntryPoint());
            }
            for (String s : seen) println("    " + s);
            println("    total: " + seen.size());
        }
    }
}
