import ghidra.app.script.GhidraScript;
import ghidra.program.model.symbol.*;
import ghidra.program.model.listing.Function;
import ghidra.program.model.address.Address;
import java.util.*;

public class ImportRefs extends GhidraScript {
    @Override
    public void run() throws Exception {
        SymbolTable st = currentProgram.getSymbolTable();
        for (String name : getScriptArgs()) {
            println("=== " + name);
            Set<String> seen = new TreeSet<>();
            for (Symbol s : st.getSymbols(name)) {
                for (Reference r : getReferencesTo(s.getAddress())) {
                    Function f = getFunctionContaining(r.getFromAddress());
                    seen.add(f == null ? r.getFromAddress() + " (no function)" : f.getName() + " @ " + f.getEntryPoint());
                    // one level up: who calls the thunk/caller
                    if (f != null && s.getAddress().equals(f.getEntryPoint()) == false) {
                        for (Reference r2 : getReferencesTo(f.getEntryPoint())) {
                            Function g = getFunctionContaining(r2.getFromAddress());
                            if (g != null) seen.add("   <- " + g.getName() + " @ " + g.getEntryPoint());
                        }
                    }
                }
            }
            for (String x : seen) println("  " + x);
            println("  total: " + seen.size());
        }
        // string references: AnticheatMgr
        for (Address a : findBytes(null, "AnticheatMgr", 20)) {
            println("=== string AnticheatMgr @ " + a);
            for (Reference r : getReferencesTo(a)) {
                Function f = getFunctionContaining(r.getFromAddress());
                println("  ref from " + (f == null ? r.getFromAddress().toString() : f.getName() + " @ " + f.getEntryPoint()));
            }
        }
    }
}
