#!/usr/bin/env python3
"""Which Lua binding sends each client-to-server packet, and how the UI calls it.

A sender site (senders.yaml) sits in a function; when that function is one of the Lua
bindings (lua-bindings.yaml), the binding's name is what the UI calls, and the UI corpus
shows the arguments it passes -- the best names for the packet's fields, at L2, once a
reader has checked the binding writes them in that order.

  python3 tools/extract/sender_bindings.py <Extensions.dll> <corpus dir> --build <id> --out <file>
"""

import argparse
import hashlib
import importlib.util
import os
import re
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))


def load_image(path):
    spec = importlib.util.spec_from_file_location("opcode_names", os.path.join(HERE, "opcode_names.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Image(path)


def function_start(image, va):
    """Scan back for `push ebp; mov ebp, esp` after padding, the compiler's prologue."""
    data, off = image.data, image.offset(va)
    for p in range(off, off - 0x4000, -1):
        if data[p:p + 3] == b"\x55\x8b\xec" and data[p - 1] in (0xCC, 0xC3, 0x90):
            return va - (off - p)
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("dll")
    parser.add_argument("corpus_dir")
    parser.add_argument("--build", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--functions", help="'<opcode> <function VA>' lines from tools/ghidra/scripts/FuncAt.java: exact "
                        "function boundaries; without it a prologue scan and a nearest-binding fallback are used")
    args = parser.parse_args()
    exact = {}
    if args.functions and os.path.isfile(args.functions):
        with open(args.functions, encoding="utf-8") as handle:
            for line in handle:
                parts = line.split()
                if len(parts) == 2 and parts[1] != "no-function":
                    exact[int(parts[0], 16)] = int(parts[1], 16)
    image = load_image(args.dll)
    symbols = os.path.join(ROOT, "client", "symbols", args.build)
    with open(os.path.join(symbols, "senders.yaml"), encoding="utf-8") as handle:
        senders = yaml.safe_load(handle)["senders"]
    with open(os.path.join(symbols, "lua-bindings.yaml"), encoding="utf-8") as handle:
        bindings = yaml.safe_load(handle)
    table = bindings.get("bindings", bindings)
    by_rva = {}
    for name, value in table.items():
        if isinstance(value, int) or (isinstance(value, str) and value.startswith("0x")):
            by_rva.setdefault(int(value, 16) if isinstance(value, str) else value, []).append(name)
    starts = sorted(by_rva)

    lua = {}
    for directory, _, files in os.walk(args.corpus_dir):
        for filename in files:
            if filename.endswith(".lua"):
                path = os.path.join(directory, filename)
                with open(path, encoding="utf-8-sig", errors="replace") as handle:
                    lua[os.path.relpath(path, args.corpus_dir).replace(os.sep, "/")] = handle.read()

    results = {}
    for key, entry in senders.items():
        opcode = int(key, 16) if isinstance(key, str) else int(key)
        site = 0x10000000 + int(entry["sender_site_rva"], 16)
        if opcode in exact:
            start = exact[opcode]
            names = by_rva.get(start - 0x10000000)
        else:
            start = function_start(image, site)
            names = by_rva.get(start - 0x10000000) if start else None
        if not names and opcode not in exact:
            # no prologue: the nearest binding entry below the site, provided no int3 padding
            # (a function boundary) lies between them
            import bisect
            k = bisect.bisect_right(starts, site - 0x10000000) - 1
            if k >= 0:
                candidate = starts[k]
                between = image.data[image.offset(0x10000000 + candidate):image.offset(site)]
                if b"\xcc\xcc" not in between and len(between) < 0x2000:
                    start, names = 0x10000000 + candidate, by_rva[candidate]
        if not names:
            continue
        calls = []
        ambiguous = set(bindings.get("ambiguous") or [])
        for name in names:
            # `C_Table.Name(` is a call of the binding; a bare `Name(` is only trusted for a
            # name long and specific enough not to be a frame method or a local function
            qualified = re.compile(r"\b[A-Za-z_]\w*\." + re.escape(name) + r"\s*\(([^()]*(?:\([^()]*\)[^()]*)*)\)")
            bare = re.compile(r"(?<![\w.:])" + re.escape(name) + r"\s*\(([^()]*(?:\([^()]*\)[^()]*)*)\)")
            patterns = [qualified] + ([bare] if len(name) >= 12 and name not in ambiguous else [])
            for pattern in patterns:
                for rel, text in lua.items():
                    for match in pattern.finditer(text):
                        args_text = match.group(1).strip()
                        if len(calls) < 6:
                            calls.append({"file": rel, "line": text.count("\n", 0, match.start()) + 1,
                                          "args": [a.strip() for a in args_text.split(",")] if args_text else []})
        results[opcode] = {"binding": names[0], "function_rva": f"{start - 0x10000000:#010x}",
                           "aliases": names[1:], "calls": calls}

    with open(args.out, "w", encoding="utf-8") as out:
        print("# Generated by tools/extract/sender_bindings.py -- do not hand-edit.", file=out)
        print(f"build: {args.build}", file=out)
        print(f"sha256: {hashlib.sha256(image.data).hexdigest()}", file=out)
        print("# Per client-to-server opcode: the Lua binding whose function contains the sender site,", file=out)
        print("# and up to six calls of it in the UI corpus with the arguments as written there (L2).", file=out)
        print(f"opcodes: {len(results)}", file=out)
        print("senders:", file=out)
        for opcode in sorted(results):
            r = results[opcode]
            print(f"  {opcode:#06x}:", file=out)
            print(f"    binding: {r['binding']}", file=out)
            print(f"    function_rva: \"{r['function_rva']}\"", file=out)
            if r["aliases"]:
                print(f"    aliases: [{', '.join(r['aliases'])}]", file=out)
            print("    calls:", file=out) if r["calls"] else print("    calls: []", file=out)
            for call in r["calls"]:
                args_repr = ", ".join('"' + a.replace('"', "'") + '"' for a in call["args"])
                print(f"      - {{file: \"{call['file']}\", line: {call['line']}, args: [{args_repr}]}}", file=out)
    print(f"{len(results)} senders are Lua bindings -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
