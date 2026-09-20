// Decompile the function containing each listed VA and print, per opcode, the CDataStore
// calls in the C text: PutData sizes, PutString, and any other call between the opcode
// write and the send. Input file: one line per entry, "<hex VA> <opcode>".
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import java.io.*;
import java.util.*;
import java.util.regex.*;

public class SenderC extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        BufferedReader in = new BufferedReader(new FileReader(args[0]));
        DecompInterface ifc = new DecompInterface();
        ifc.openProgram(currentProgram);
        Pattern call = Pattern.compile("\\(\\*DAT_10bc90(cc|dc|d8|fc)\\)\\(([^;]*)\\);");
        String line;
        while ((line = in.readLine()) != null) {
            String[] parts = line.trim().split("\\s+");
            if (parts.length < 2) continue;
            Address addr = currentProgram.getImageBase().getNewAddress(Long.parseLong(parts[0], 16));
            Function f = getFunctionContaining(addr);
            println("=== " + parts[1] + " " + (f == null ? "no-function" : f.getName()));
            if (f == null) continue;
            DecompileResults r = ifc.decompileFunction(f, 45, monitor);
            if (!r.decompileCompleted()) { println("  decompile-failed"); continue; }
            for (String l : r.getDecompiledFunction().getC().split("\n")) {
                Matcher m = call.matcher(l);
                if (m.find()) println("  " + m.group(1) + " " + m.group(2).trim());
                else if (l.contains("FUN_1008d690") || l.contains("FUN_100e08b0")) println("  helper " + l.trim());
            }
        }
        println("done");
    }
}
