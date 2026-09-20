#!/usr/bin/env python3
"""Trace the read cursor through a decompiled function, the way the eye does.

A handler or a deserialization helper reads a `CDataStore` by advancing the read
position at `+0x14` and taking bytes at `base(+4) + pos`. This prints, in source order,
every advance and every store into the record being filled, so a reader can line up
"read 4 bytes" with "store at record +0x18" without scrolling through the decompilation.

It is a reading aid over `DumpC.java`'s output, like `handler_brief.py`: it proves
nothing on its own and its output is never a layout. The fiche still says what a human
read.

    tools/helper_trace.py <file.c> [more.c ...]
"""
import re
import sys

ADV = re.compile(r"\*\(int \*\)\((\w+) \+ 0x14\) =\s*(?:\*\(int \*\)\(\w+ \+ 0x14\) \+ )?(?:(\w+) \+ )?(0x[0-9a-f]+|\d+)")
READ = re.compile(r"=\s*\*\((undefined4|undefined1|undefined8|uint|int|char|ushort|byte|float) \*\)\(")
STORE = re.compile(r"\*\((?:undefined4|undefined1|undefined8|ulonglong|int|uint) \*\)\((?:\*?\w+(?:\[\d+\])? \+ )?(0x[0-9a-f]+)\) =")
SCAN = re.compile(r"while \((\w+) != '\\0'\)")
CALL = re.compile(r"(FUN_[0-9a-f]{8}|\(\*\(code \*\)0x[0-9a-f]+\))\(")

WIDTH = {"undefined1": 1, "char": 1, "byte": 1, "ushort": 2, "undefined8": 8,
         "undefined4": 4, "uint": 4, "int": 4, "float": 4}


def trace(path):
    print(f"=== {path}")
    for n, line in enumerate(open(path, encoding="utf-8"), 1):
        line = line.strip()
        parts = []
        m = READ.search(line)
        if m:
            parts.append(f"read {WIDTH.get(m.group(1), '?')}")
        if SCAN.search(line):
            parts.append("STRING scan")
        m = ADV.search(line)
        if m:
            parts.append(f"pos += {m.group(3)}" if not m.group(2) else f"pos = {m.group(2)} + {m.group(3)}")
        m = STORE.search(line)
        if m and not (m.group(1) == "0x14" and any(x.startswith("pos") for x in parts)):
            parts.append(f"-> record {m.group(1)}")
        m = CALL.search(line)
        if m and not parts:
            parts.append(f"call {m.group(1)}")
        if parts:
            print(f"  {n:4d}  {' | '.join(parts)}")


if __name__ == "__main__":
    for path in sys.argv[1:]:
        trace(path)
