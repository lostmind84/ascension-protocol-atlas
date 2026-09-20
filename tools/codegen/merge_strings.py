#!/usr/bin/env python3
"""Write the string literals a handler references into its fiche as `client_strings:`.

A handler's strings are the closest thing to its meaning the binary offers for free: the
Lua event it fires (`WILDCARD_ENTRY_LEARNED`), the format strings it logs, the names it
looks up. They are recorded verbatim, filtered only of obvious noise (paths, format-only
strings, single tokens under three characters). Idempotent: an existing block is replaced.

  python3 tools/codegen/merge_strings.py --build <id>
"""

import argparse
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BLOCK = re.compile(r"^client_strings:.*?(?=^\S)", re.M | re.S)
NOISE = re.compile(r"^(%[sd]|\\n|[^A-Za-z]*)$|\.cpp$|\.h$|^C:\\|^Usage:")


def keep(text):
    return len(text) >= 3 and not NOISE.search(text)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--build", required=True)
    args = parser.parse_args()

    path = os.path.join(ROOT, "client", "symbols", args.build, "handler-strings.yaml")
    with open(path, encoding="utf-8") as handle:
        strings = yaml.safe_load(handle)["handlers"]
    strings = {(int(k, 16) if isinstance(k, str) else int(k)): (v or {}).get("strings") or []
               for k, v in strings.items()}

    directory = os.path.join(ROOT, "protocol", "opcodes")
    written = 0
    for filename in sorted(os.listdir(directory)):
        if not filename.endswith(".yaml"):
            continue
        opcode = int(filename.split("-", 1)[0], 16)
        found = [s for s in strings.get(opcode, []) if keep(s)]
        if not found:
            continue
        file_path = os.path.join(directory, filename)
        with open(file_path, encoding="utf-8") as handle:
            text = handle.read()
        lines = ["client_strings:   # literals the handler references, from its decompilation"]
        for s in found[:24]:
            lines.append("  - " + yaml.safe_dump(s, default_style='"', width=10000).strip())
        block = "\n".join(lines) + "\n"
        if BLOCK.search(text):
            updated = BLOCK.sub(lambda _: block + "\n", text, count=1)
        else:
            updated = text.replace("provenance:", block + "\nprovenance:", 1)
        if updated != text:
            with open(file_path, "w", encoding="utf-8") as handle:
                handle.write(updated)
            written += 1
    print(f"client_strings written into {written} fiches")
    return 0


if __name__ == "__main__":
    sys.exit(main())
