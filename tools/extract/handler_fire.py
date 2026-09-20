#!/usr/bin/env python3
"""Read, in each handler's decompilation, what it fires and with which packet fields.

Input: the per-handler C files written by tools/ghidra/scripts/DumpC.java. For each
handler the script records

  reads:  the packet loads in order -- the variable each lands in and its width (a loop's
          reads nested as {repeat: <count variable>, reads: [...]}), from
          the cursor store-back idiom (`*(int *)(pkt + 0x14) = ... + N`), plus every call
          to FUN_100d3680, the length-prefixed string reader (u32 length, then the bytes,
          no NUL), recorded as width `lpstring`;
  fires:  every event firing, with the event name, the printf-like format the binary
          passes (`"%u%u%u"`, or `&DAT_...` resolved to its text) and, when the handler
          calls the formatter FUN_10278c90 itself, which read variable fills each
          position. The wrapper helpers (FUN_100b9620 and family) take the same format
          but hide the arguments behind stack slots Ghidra does not name, so for them
          only the format is recorded.

`args` is the proof that a Lua event argument IS a packet field: position i of the
format is filled by read k. Without it, a format of the same length as the layout is a
coincidence until someone reads the handler.

  python3 tools/extract/handler_fire.py <c dir> <Extensions.dll> --build <id> --out <file>
"""

import argparse
import hashlib
import importlib.util
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FORMATTER = "FUN_10278c90"
WRAPPERS = {"FUN_100b9620", "FUN_100b94b0", "FUN_100b96e0", "FUN_100b9560", "FUN_100eafb0",
            "FUN_1025a6c0", "FUN_100d0a50", "FUN_100e09f0", "FUN_10129bd0", "FUN_1011a5b0",
            "FUN_100d0bd0"}
STORE = re.compile(r'^\s*\*\(int \*\)\((\w+) \+ 0x14\) = (.+);$')
LOAD = re.compile(r'^\s*(\w+) = \*\((?:undefined|uint|int|float|char|short|ushort|byte|size_t|undefined[1248])[^)]*\*\)\(')
EVENT_SYM = re.compile(r's_([A-Z][A-Z0-9_]{3,})_10b[0-9a-f]{5}')
EVENT_LIT = re.compile(r'FUN_10086e30\("([A-Z][A-Z0-9_]{3,})",0x[0-9a-f]+\)')
FMT_DIRECT = re.compile(r'FUN_10278c90\(([^,()]+),("(%[a-z]+)*"|&DAT_10b[0-9a-f]{5})((?:,[^;]*)?)\);')
FMT_REF = re.compile(r'&DAT_(10b[0-9a-f]{5})')
IDENT = re.compile(r'[A-Za-z_]\w*')
LPSTRING = re.compile(r'FUN_100d3680\((?:&?(\w+))?')


def load_image(path):
    spec = importlib.util.spec_from_file_location("opcode_names", os.path.join(HERE, "opcode_names.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Image(path)


def parse(text, image):
    lines = text.splitlines()
    pkt = {"in_stack_00000010"}
    for line in lines:
        m = re.match(r'^\s*(\w+) = in_stack_00000010;$', line)
        if m:
            pkt.add(m.group(1))
    reads, last_abs = [], {}
    # Loop structure: Ghidra prints one statement per line with braces on the line, so the
    # depth is a running count. A loop header opens a frame; reads made while it is open
    # belong to it; when its brace closes, the frame becomes a {repeat, reads} entry of the
    # enclosing list -- the counted record the flat asm idiom cannot show.
    depth, frames = 0, [{"depth": -1, "count": None, "reads": reads, "kind": "top"}]
    LOOP_WHILE = re.compile(r'^\s*while \((\w+) != 0\) \{')
    LOOP_WHILE_LT = re.compile(r'^\s*while \((\w+) < (\w+)\) \{')
    LOOP_FOR = re.compile(r'^\s*for \([^;]*; (\w+) != 0; [^)]*\) \{')
    LOOP_FOR_LT = re.compile(r'^\s*for \([^;]*; (\w+) < (\w+); [^)]*\) \{')
    LOOP_DO = re.compile(r'^\s*do \{')
    DO_END = re.compile(r'^\s*\} while \((\w+) < (\w+)\);|^\s*\} while \((\w+) != 0\);|^\s*\} while \((\w+) > (\w+)\);')

    def close_frames(new_depth):
        while frames[-1]["kind"] != "top" and new_depth <= frames[-1]["depth"]:
            frame = frames.pop()
            if frame["reads"]:
                frames[-1]["reads"].append({"repeat": frame["count"], "reads": frame["reads"]})

    for i, line in enumerate(lines):
        target = frames[-1]["reads"]
        header = LOOP_WHILE.match(line) or LOOP_FOR.match(line)
        header_lt = LOOP_WHILE_LT.match(line) or LOOP_FOR_LT.match(line)
        if header:
            frames.append({"depth": depth, "count": header.group(1), "reads": [], "kind": "loop"})
        elif header_lt:
            frames.append({"depth": depth, "count": header_lt.group(2), "reads": [], "kind": "loop"})
        elif LOOP_DO.match(line):
            frames.append({"depth": depth, "count": None, "reads": [], "kind": "loop"})
        end = DO_END.match(line)
        if end and frames[-1]["kind"] == "loop" and frames[-1]["count"] is None:
            frames[-1]["count"] = end.group(2) or end.group(3) or end.group(4)
        opened, closed = line.count("{"), line.count("}")
        # a closing brace at the loop's depth ends its frame (after this line's own read)
        lp = LPSTRING.search(line)
        if lp:
            # FUN_100d3680(this=packet, &out): u32 length, then that many bytes, into a std::string.
            # It advances the cursor itself, so the handler shows only the call.
            target.append({"var": lp.group(1), "width": "lpstring"})
            depth += opened - closed
            close_frames(depth)
            continue
        m = STORE.match(line)
        if not m or m.group(1) not in pkt:
            depth += opened - closed
            if closed and not end:
                close_frames(depth)
            elif end:
                close_frames(depth)
            continue
        rhs = m.group(2)
        width = None
        rel = re.match(r'^\*\(int \*\)\(\w+ \+ 0x14\) \+ (0x[0-9a-f]+|\d+)$', rhs)
        absm = re.match(r'^(\w+) \+ (0x[0-9a-f]+|\d+)$', rhs)
        if rel:
            width = int(rel.group(1), 0)
        elif absm:
            base, offset = absm.group(1), int(absm.group(2), 0)
            width = offset - last_abs.get(base, 0)
            last_abs[base] = offset
        elif re.match(r'^\w+$', rhs):
            last_abs[rhs] = 0
            continue
        elif re.search(r"\+ 1\) - |\+ 1 \+ \(|- \(int\)\w+\)$", rhs):
            width = "cstring"   # the cursor moved to one past a NUL the handler scanned for
        else:
            width = "var"       # a string or a computed skip
        length_var = None
        skip = re.match(r'^\*\(int \*\)\(\w+ \+ 0x14\) \+ (?:\(int\))?(\w+)$', rhs) or re.match(r'^\w+ \+ (?:\(int\))?(\w+)$', rhs)
        if width == "var" and skip and not re.match(r'^0x|^\d', skip.group(1)):
            length_var = skip.group(1)
        var = None
        loads = []
        for back in range(i - 1, max(-1, i - 8), -1):
            if STORE.match(lines[back]):
                break
            lm = LOAD.match(lines[back])
            if lm:
                rhs_load = lines[back].split("=", 1)[1]
                # `x = *(int *)(pkt + 0x14)` / `(pkt + 4)` load the cursor and the base, not a field
                if not re.search(r'\(\w+ \+ (0x14|4)\)\s*;', rhs_load):
                    loads.append(lm.group(1))
        if loads:
            var = loads[0]
        if isinstance(width, int) and width <= 0:
            width = "var"       # the cursor arithmetic changed base: not a width
        # One store-back after several loads is several fields (Ghidra folds `a = p[0];
        # b = p[1]; cursor += 8` into one step): split evenly when the loads say so.
        if isinstance(width, int) and len(loads) > 1 and width % len(loads) == 0 and width // len(loads) in (1, 2, 4, 8):
            each = width // len(loads)
            for name in reversed(loads):
                target.append({"var": name, "width": each, "length_var": None})
        else:
            target.append({"var": var, "width": width, "length_var": length_var})
        depth += opened - closed
        if closed:
            close_frames(depth)
    close_frames(-1)

    # A u32 length followed by a skip of that many bytes is the length-prefixed string read
    # inline (memcpy) instead of through FUN_100d3680: one field, not two.
    def collapse(entries):
        out = []
        for read in entries:
            if "repeat" in read:
                out.append({"repeat": read["repeat"], "reads": collapse(read["reads"])})
            elif (read["width"] == "var" and out and "repeat" not in out[-1] and out[-1]["width"] == 4
                  and read.get("length_var") and read["length_var"] == out[-1]["var"]):
                out[-1] = {"var": read["var"] or out[-1]["var"], "width": "lpstring"}
            else:
                out.append({"var": read["var"], "width": read["width"]})
        return out
    reads = collapse(reads)

    def flatten(entries):
        for read in entries:
            if "repeat" in read:
                yield from flatten(read["reads"])
            else:
                yield read
    read_vars = {r["var"]: k for k, r in enumerate(flatten(reads)) if r["var"]}

    fires, current = [], None
    for line in lines:
        sym = EVENT_SYM.search(line) or EVENT_LIT.search(line)
        if sym:
            current = sym.group(1)
        m = FMT_DIRECT.search(line)
        if m:
            fmt = m.group(2)
            if fmt.startswith("&DAT_"):
                fmt = image.string(int(fmt[5:], 16)) or "?"
            else:
                fmt = fmt.strip('"')
            args = [a.strip() for a in m.group(4).split(",") if a.strip()]
            mapping = []
            for arg in args:
                idents = [x for x in IDENT.findall(arg) if x in read_vars]
                mapping.append(read_vars[idents[0]] if len(idents) == 1 else None)
            fires.append({"event": current, "format": fmt, "helper": FORMATTER, "args": mapping})
            continue
        wm = re.search(r'\b(FUN_1[0-9a-f]{7})\(', line)
        if wm and wm.group(1) in WRAPPERS and current:
            fmt = None
            head = "\n".join(lines[: lines.index(line) + 1])
            refs = FMT_REF.findall(head)
            for ref in reversed(refs):
                text = image.string(int(ref, 16))
                if text and text.startswith("%"):
                    fmt = text
                    break
            fires.append({"event": current, "format": fmt, "helper": wm.group(1), "args": None})
    return reads, fires


def render(entries):
    """Reads as a YAML flow list: [var, width] leaves and {repeat: countVar, reads: [...]} records."""
    parts = []
    for read in entries:
        if "repeat" in read:
            parts.append("{repeat: " + (read["repeat"] or "null") + ", reads: " + render(read["reads"]) + "}")
        else:
            parts.append(f"[{read['var'] or 'null'}, {read['width']}]")
    return "[" + ", ".join(parts) + "]"


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("cdir")
    parser.add_argument("dll")
    parser.add_argument("--build", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    image = load_image(args.dll)

    results = {}
    for filename in sorted(os.listdir(args.cdir)):
        if not filename.endswith(".c"):
            continue
        opcode = int(filename[:-2], 16)
        with open(os.path.join(args.cdir, filename), encoding="utf-8", errors="replace") as handle:
            text = handle.read()
        reads, fires = parse(text, image)
        if reads or fires:
            results[opcode] = (reads, fires)

    with open(args.out, "w", encoding="utf-8") as out:
        print("# Generated by tools/extract/handler_fire.py -- do not hand-edit.", file=out)
        print(f"build: {args.build}", file=out)
        print(f"sha256: {hashlib.sha256(image.data).hexdigest()}", file=out)
        print("# reads: packet loads in order (variable, width); fires: event, printf-like format,", file=out)
        print("# helper, and for direct FUN_10278c90 calls which read fills each format position.", file=out)
        print(f"handlers_with_reads: {sum(1 for r, f in results.values() if r)}", file=out)
        print(f"handlers_with_fires: {sum(1 for r, f in results.values() if f)}", file=out)
        print(f"fires_with_args: {sum(1 for r, f in results.values() for x in f if x['args'] is not None)}", file=out)
        print("handlers:", file=out)
        for opcode in sorted(results):
            reads, fires = results[opcode]
            print(f"  {opcode:#06x}:", file=out)
            print("    reads: " + render(reads), file=out)
            print("    fires:", file=out) if fires else print("    fires: []", file=out)
            for f in fires:
                print(f"      - event: {f['event'] or 'null'}", file=out)
                print(f"        format: {('\"' + f['format'] + '\"') if f['format'] else 'null'}", file=out)
                print(f"        helper: {f['helper']}", file=out)
                if f["args"] is not None:
                    print("        args: [" + ", ".join("null" if a is None else str(a) for a in f["args"]) + "]", file=out)
    print(f"{len(results)} handlers -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
