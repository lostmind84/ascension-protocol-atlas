#!/usr/bin/env python3
"""Name a skeleton layout's fields after reading the handler, and say where the names came from.

  tools/name_fields.py 0x0593 challengeID level response field_3 ... [--summary "..."] [--source "..."]

Positional names replace field_0.. in order (`-` or `field_N` keeps the placeholder). Types
are left alone unless given as name:type. The fiche becomes `hypothetical` with a provenance
entry naming the handler decompilation and the Lua/format evidence that supplied the names;
the widths keep their L3 grade. A note line goes under the layout.
"""

import argparse
import glob
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("opcode")
    parser.add_argument("names", nargs="+")
    parser.add_argument("--summary", help="replace the summary")
    parser.add_argument("--source", default="the decompiled handler (tools/ghidra/scripts/DumpC.java) read next to client_fire and client_events",
                        help="what the names were read from")
    parser.add_argument("--note", default="", help="a line to keep under the layout")
    args = parser.parse_args()

    opcode = int(args.opcode, 16)
    path = glob.glob(os.path.join(ROOT, "protocol", "opcodes", f"{opcode:#06x}-*.yaml"))[0]
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    fiche = yaml.safe_load(text)
    layout = fiche.get("layout") or []
    flat = [f for f in layout if "repeat" not in f]
    if len(args.names) > len(flat):
        sys.exit(f"{len(args.names)} names for {len(flat)} fields")
    for index, spec in enumerate(args.names):
        name, _, kind = spec.partition(":")
        if name in ("-", f"field_{index}") and not kind:
            continue
        old_name = flat[index].get("name")
        text = re.sub(rf"^  - name: {re.escape(str(old_name))}\n    type: (\S+)\n",
                      lambda m: f"  - name: {name or old_name}\n    type: {kind or m.group(1)}\n", text, count=1, flags=re.M)
    text = text.replace("status: unknown", "status: hypothetical", 1)
    if args.summary:
        text = re.sub(r"^summary: >\n(?:  [^\n]*\n)+", "summary: >\n" + "".join(f"  {line}\n" for line in args.summary.split("\n")), text, count=1, flags=re.M)
    note = f"# Names: {args.source}." + (f" {args.note}" if args.note else "")
    if note not in text:
        text = re.sub(r"^(# Widths and order[^\n]*\n)", lambda m: m.group(1) + note + "\n", text, count=1, flags=re.M)
    prov = ("  - level: L3\n"
            f"    source: \"{args.source}\"\n"
            "    claim: \"the field names, from how the handler uses each read\"\n")
    if prov not in text:
        text = text.replace("provenance:\n", "provenance:\n" + prov, 1)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    print(f"named {opcode:#06x}: {', '.join(n.split(':')[0] for n in args.names)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
