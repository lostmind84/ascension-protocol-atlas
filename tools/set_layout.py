#!/usr/bin/env python3
"""Replace a fiche's layout with one read from the decompiled handler, repeat blocks included.

  tools/set_layout.py 0x0596 --layout layout.yaml --summary "..." [--source "..."] [--evidence L3]

`layout.yaml` (or stdin with `-`) is the YAML list that goes under `layout:`; every field
without an `evidence` gets --evidence. The fiche becomes `hypothetical`, keeps its other
blocks, and gains a provenance entry naming the source. The generated-layout comment
lines are dropped: this layout was read, not extracted.
"""

import argparse
import glob
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def grade(entries, level):
    for entry in entries:
        if "repeat" in entry:
            grade(entry.get("fields") or [], level)
        else:
            entry.setdefault("evidence", level)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("opcode")
    parser.add_argument("--layout", required=True, help="YAML file with the layout list, or - for stdin")
    parser.add_argument("--summary")
    parser.add_argument("--evidence", default="L3")
    parser.add_argument("--source", default="the decompiled handler (tools/ghidra/scripts/DumpC.java), read by hand")
    parser.add_argument("--note", default="")
    args = parser.parse_args()

    opcode = int(args.opcode, 16)
    path = glob.glob(os.path.join(ROOT, "protocol", "opcodes", f"{opcode:#06x}-*.yaml"))[0]
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    raw = sys.stdin.read() if args.layout == "-" else open(args.layout, encoding="utf-8").read()
    entries = yaml.safe_load(raw)
    if not isinstance(entries, list):
        sys.exit("the layout must be a YAML list")
    grade(entries, args.evidence)
    rendered = yaml.safe_dump(entries, sort_keys=False, default_flow_style=False, width=1000)
    block = "layout:\n" + "".join("  " + line + "\n" for line in rendered.rstrip("\n").split("\n"))
    block += f"# Read from {args.source}." + (f" {args.note}\n" if args.note else "\n")
    text = re.sub(r"^layout:.*?(?=^\S)", lambda _: block + "\n", text, count=1, flags=re.M | re.S)
    text = text.replace("status: unknown", "status: hypothetical", 1)
    if args.summary:
        text = re.sub(r"^summary: >\n(?:  [^\n]*\n)+", "summary: >\n" + "".join(f"  {line}\n" for line in args.summary.split("\n")), text, count=1, flags=re.M)
    prov = (f"  - level: {args.evidence}\n"
            f"    source: \"{args.source}\"\n"
            "    claim: \"the layout: widths, order, repeat structure and field names\"\n")
    if prov not in text:
        text = text.replace("provenance:\n", "provenance:\n" + prov, 1)
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    print(f"layout set on {opcode:#06x} ({len(entries)} top-level entries)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
