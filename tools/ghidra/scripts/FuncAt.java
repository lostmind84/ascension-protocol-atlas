// For each "<hex VA> <label>" line of the input file, print "<label> <function entry VA>" for the
// function containing the VA, or "no-function", so a sender site can be tied to its binding exactly.
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import java.io.*;

public class FuncAt extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        BufferedReader in = new BufferedReader(new FileReader(args[0]));
        PrintWriter out = new PrintWriter(new FileWriter(args[1]));
        String line;
        while ((line = in.readLine()) != null) {
            String[] parts = line.trim().split("\\s+");
            if (parts.length < 2) continue;
            Address addr = currentProgram.getImageBase().getNewAddress(Long.parseLong(parts[0], 16));
            Function f = getFunctionContaining(addr);
            out.println(parts[1] + " " + (f == null ? "no-function" : f.getEntryPoint().toString()));
        }
        out.close();
        println("done");
    }
}
