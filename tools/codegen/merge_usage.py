#!/usr/bin/env python3
"""Write `used_by_server:` into the fiches from client/server-usage.yaml.

Idempotent: a previously written block is replaced, and a fiche is never otherwise
touched. Fiches that gain a server usage and have no `used_by_server` yet get the block
inserted before `provenance:`.

  python3 tools/codegen/merge_usage.py
"""

import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BLOCK = re.compile(r"^used_by_server:.*?(?=^\S)", re.M | re.S)


def render(entry):
    lines = ["used_by_server:   # the CoA server module sends or handles this"]
    for name in entry.get("server_names") or []:
        lines.append(f"  server_name: {name}")
    lines.append("  files:")
    for path in entry["files"]:
        lines.append(f"    - {path}")
    return "\n".join(lines) + "\n"


def main():
    with open(os.path.join(ROOT, "client", "server-usage.yaml"), encoding="utf-8") as handle:
        usage = yaml.safe_load(handle)["opcodes"]
    usage = {(int(k, 16) if isinstance(k, str) else int(k)): v for k, v in usage.items()}

    directory = os.path.join(ROOT, "protocol", "opcodes")
    written = missing = 0
    covered = set()
    for filename in sorted(os.listdir(directory)):
        if not filename.endswith(".yaml"):
            continue
        opcode = int(filename.split("-", 1)[0], 16)
        entry = usage.get(opcode)
        if entry is None:
            continue
        covered.add(opcode)
        path = os.path.join(directory, filename)
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        block = render(entry)
        if BLOCK.search(text):
            # BLOCK swallows the blank line that separates the section from the next key;
            # put it back, or every rerun strips one and the regenerate check never settles.
            updated = BLOCK.sub(lambda _: block + "\n", text, count=1)
        else:
            updated = text.replace("provenance:", block + "\nprovenance:", 1)
        if updated != text:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(updated)
            written += 1
    for opcode in usage:
        if opcode not in covered:
            missing += 1
            print(f"  no fiche for {opcode:#06x} (server uses it)")
    print(f"written: {written}; server opcodes without a fiche: {missing}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
