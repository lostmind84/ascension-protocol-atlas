#!/usr/bin/env python3
"""Write what each handler fires into its fiche, and name the fields the binary proves.

From client/symbols/<build>/handler-fire.yaml every fiche whose handler fires an event
gets a `client_fire:` block (event, format, helper, and the read-to-argument mapping when
the handler calls the formatter itself). Replaced in place on each run.

A skeleton layout (`field_0`, `field_1`, ...) is renamed only when three things agree:
the handler's read count equals the layout's field count, the fire's `args` mapping fills
every format position from a distinct read, and `client_events` carries as many Lua
argument names as the format has specifiers. The name is then the Lua argument's (L2),
the position is the binary's (L3), and the fiche says so in a comment and in provenance.
Anything short of that is left as `field_N`.

  python3 tools/codegen/merge_fire.py --build <id>
"""

import argparse
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BLOCK = re.compile(r"^client_fire:.*?(?=^\S)", re.M | re.S)
STUB_LAYOUT = "layout: []   # unknown"
# The generated block ends at its own marker comment, which no hand fiche carries: match
# lazily up to it (a field-by-field alternation backtracks exponentially on nested blocks).
FALLBACK = re.compile(
    r"^layout:\n.*?# Widths and order, from the handler's DECOMPILED read sequence[^\n]*\n(?:#[^\n]*\n)*", re.M | re.S)
ASM = re.compile(
    r"^layout:\n(?:  - name: field_\d+\n    type: \S+\n    evidence: L3\n)*"
    r"# Widths and order, read out of the handler at[^\n]*\n(?:#[^\n]*\n)*", re.M)
TYPE = {1: "u8", 2: "u16", 4: "u32", 8: "u64", "var": "unknown", "lpstring": "lpstring", "cstring": "cstring"}


def flatten(reads):
    for read in reads:
        if isinstance(read, dict) and "repeat" in read:
            yield from flatten(read["reads"])
        else:
            yield read


def read_block(reads, symbols, origin):
    lines = ["layout:"]
    counter = [0]
    names = {}

    def emit(entries, indent):
        for read in entries:
            if isinstance(read, dict) and "repeat" in read:
                count = names.get(read["repeat"], "unknown")
                lines.append(f"{indent}- repeat: {count}")
                lines.append(f"{indent}  fields:")
                emit(read["reads"], indent + "    ")
                continue
            var = read[0] if isinstance(read, list) else read.get("var")
            width = read[1] if isinstance(read, list) else read["width"]
            kind = TYPE.get(width, f"bytes_{width}")
            name = f"field_{counter[0]}"
            counter[0] += 1
            if var:
                names.setdefault(var, name)
            lines.extend([f"{indent}- name: {name}", f"{indent}  type: {kind}", f"{indent}  evidence: L3"])
    emit(reads, "  ")
    lines.append(f"# Widths and order, from the handler's DECOMPILED read sequence ({symbols}/handler-fire.yaml);")
    lines.append(f"# {origin}. `lpstring` is FUN_100d3680: u32 length then that many bytes, no NUL.")
    lines.append("# A bytes_N field is a block copy of N bytes, `unknown` a computed length. Names are")
    lines.append("# placeholders; check the handler before trusting a width.")
    return "\n".join(lines) + "\n"
SPEC = re.compile(r"%[a-z]")
IDENT = re.compile(r"^[A-Za-z_]\w*$")
WIDTH_OK = {"u": {4, 1, 2}, "d": {4, 1, 2}, "b": {1, 4}, "f": {4}, "s": {"var", 4, "lpstring", "cstring"}}


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--build", required=True)
    args = parser.parse_args()

    symbols = f"client/symbols/{args.build}"
    with open(os.path.join(ROOT, symbols, "handler-fire.yaml"), encoding="utf-8") as handle:
        fire = yaml.safe_load(handle)["handlers"]
    fire = {(int(k, 16) if isinstance(k, str) else int(k)): v for k, v in fire.items()}

    directory = os.path.join(ROOT, "protocol", "opcodes")
    blocks = named = fallback = 0
    for filename in sorted(os.listdir(directory)):
        if not filename.endswith(".yaml"):
            continue
        opcode = int(filename.split("-", 1)[0], 16)
        entry = fire.get(opcode)
        if not entry or not (entry.get("fires") or entry.get("reads")):
            continue
        path = os.path.join(directory, filename)
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        original = text
        fiche = yaml.safe_load(text)

        # Second-source widths: packet_layout.py (asm idiom) found nothing, but the decompiled
        # read sequence did. Only a stub nobody has worked on is touched, and the block says
        # where it came from so a reader knows to check the handler before trusting a width.
        reads_c = entry.get("reads") or []
        if fiche.get("status") == "unknown" and "-smsg-" in filename and reads_c:
            block = None
            if STUB_LAYOUT in text:
                block = read_block(reads_c, symbols, "tools/extract/packet_layout.py found no read idiom here")
                text = text.replace(STUB_LAYOUT, block.rstrip("\n"), 1)
            elif FALLBACK.search(text):
                block = read_block(reads_c, symbols, "tools/extract/packet_layout.py found no read idiom here")
                text = FALLBACK.sub(lambda _: block, text, count=1)
            elif ASM.search(text):
                # The asm idiom cannot see FUN_100d3680's strings, and it sometimes followed a call
                # into a callee and read THAT function's cursor arithmetic (the comment then names
                # an address that is not the handler's). In both cases the decompiled sequence of
                # the handler itself is the better source and replaces the asm one -- for the
                # strings only when the inline reads agree in number, so the sequences are the same.
                asm_at = re.search(r"read out of the handler at (0x[0-9a-f]+)", text)
                handler_rva = ((fiche.get("client") or {}).get("handler") or {}).get("rva")
                elsewhere = asm_at and handler_rva and int(asm_at.group(1), 16) != int(handler_rva, 16)
                flat_c = list(flatten(reads_c))
                structured = any(isinstance(r, dict) and "repeat" in r for r in reads_c)
                has_strings = any((r[1] if isinstance(r, list) else r["width"]) == "lpstring" for r in flat_c)
                inline = [r for r in flat_c if (r[1] if isinstance(r, list) else r["width"]) != "lpstring"]
                asm_types = [str(f.get("type")) for f in (fiche.get("layout") or []) if "repeat" not in f]
                c_types = [TYPE.get(r[1] if isinstance(r, list) else r["width"], "bytes") for r in flat_c]
                if structured and c_types == asm_types:
                    block = read_block(reads_c, symbols, "the asm idiom (packet_layout.py) saw the same reads flat; the loop structure is the decompilation's")
                elif elsewhere:
                    block = read_block(reads_c, symbols, f"packet_layout.py had followed a call into {asm_at.group(1)}, not the handler")
                elif has_strings and len(inline) == len(asm_types):
                    block = read_block(reads_c, symbols, "the asm idiom (packet_layout.py) saw the same reads minus the strings")
                else:
                    # The asm idiom sees a length-prefixed string as its u32 length and stops at
                    # the copy. Viewed that way, when the asm layout is a prefix of the decompiled
                    # sequence, the two agree and the decompiled one -- longer, with the strings
                    # typed -- replaces it.
                    c_as_asm = ["u32" if t == "lpstring" else t for t in c_types]
                    if (asm_types and asm_types == c_as_asm[:len(asm_types)] and (c_types != asm_types or structured)
                            and "unknown" not in c_types):
                        block = read_block(reads_c, symbols, f"the asm idiom (packet_layout.py) saw the first {len(asm_types)} read(s) the same way and stopped")
                if block:
                    text = ASM.sub(lambda _: block, text, count=1)
            if block:
                prov = ("  - level: L3\n"
                        f"    source: \"{symbols}/handler-fire.yaml (decompiled read sequence)\"\n"
                        "    claim: \"the read widths and their order, as decompiled\"\n")
                if prov not in text:
                    text = text.replace("provenance:\n", "provenance:\n" + prov, 1)
                fiche = yaml.safe_load(text)
                fallback += 1
        if not entry.get("fires"):
            if text != original:
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(text)
            continue

        layout = fiche.get("layout") or []
        reads = list(flatten(entry.get("reads") or []))
        aligned = len(reads) == len([f for f in layout if "repeat" not in f])
        lines = [f"client_fire:   # what the handler fires, from its decompilation ({symbols}/handler-fire.yaml, L3)"]
        for f in entry["fires"]:
            lines.append(f"  - event: {f.get('event') or 'null'}")
            lines.append(f"    format: {('\"' + f['format'] + '\"') if f.get('format') else 'null'}")
            lines.append(f"    helper: {f['helper']}")
            if f.get("args") is not None:
                if aligned:
                    lines.append("    fields: [" + ", ".join("null" if a is None else f"field_{a}" for a in f["args"]) + "]"
                                 + "   # the read filling each format position")
                else:
                    lines.append("    read_slots: [" + ", ".join("null" if a is None else str(a) for a in f["args"]) + "]"
                                 + f"   # indices into the {len(reads)} reads this pass saw; the layout has {len(layout)}, so not field numbers")
        block = "\n".join(lines) + "\n"
        if BLOCK.search(text):
            updated = BLOCK.sub(lambda _: block + "\n", text, count=1)
        else:
            updated = text.replace("provenance:", block + "\nprovenance:", 1)

        # naming, only on a skeleton layout the binary and the UI agree on
        skeleton = bool(layout) and all(str(x.get("name", "")).startswith("field_") for x in layout)
        events = {e["event"]: e["args"] for e in (fiche.get("client_events") or []) if e.get("args")}
        if skeleton and aligned:
            for f in entry["fires"]:
                mapping, fmt, event = f.get("args"), f.get("format") or "", f.get("event")
                if mapping is None or not event or event not in events:
                    continue
                specs = SPEC.findall(fmt)
                names = events[event]
                if not (len(specs) == len(mapping) == len(names)):
                    continue
                if any(m is None for m in mapping) or len(set(mapping)) != len(mapping):
                    continue
                if not all(IDENT.match(n) for n in names):
                    continue
                ok = True
                for spec, k in zip(specs, mapping):
                    width = reads[k][1] if isinstance(reads[k], list) else reads[k]["width"]
                    if width not in WIDTH_OK.get(spec[1], set()):
                        ok = False
                if not ok:
                    continue
                for spec, k, name in zip(specs, mapping, names):
                    updated = re.sub(rf"^  - name: field_{k}$", f"  - name: {name}", updated, count=1, flags=re.M)
                note = (f"# Names: the Lua arguments of {event} (client/event-args.yaml, L2), at the positions the\n"
                        f"# handler fills them from its reads (handler-fire.yaml, format {fmt}, L3). Unnamed fields are\n"
                        f"# read but not passed to the event.\n")
                if note not in updated:
                    updated = re.sub(r"^(# Widths and order, read out of the handler[^\n]*\n)", lambda m: m.group(1) + note, updated, count=1, flags=re.M)
                    updated = updated.replace("# Names are placeholders and the structure is flat: a count followed by a\n"
                                              "# repeated record appears here as the count plus one record's fields.\n",
                                              "# The structure is flat: a count followed by a repeated record appears here as\n"
                                              "# the count plus one record's fields.\n", 1)
                prov = ("  - level: L2\n"
                        f"    source: \"client/event-args.yaml ({event}) joined through {symbols}/handler-fire.yaml\"\n"
                        "    claim: \"the field names, as the UI's method named after the event declares them\"\n")
                if prov not in updated:
                    updated = updated.replace("provenance:\n", "provenance:\n" + prov, 1)
                named += 1
                break

        if updated != original:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(updated)
        blocks += 1
    print(f"client_fire written into {blocks} fiches; {named} skeleton layouts named; {fallback} layouts from decompiled reads")
    return 0


if __name__ == "__main__":
    sys.exit(main())
