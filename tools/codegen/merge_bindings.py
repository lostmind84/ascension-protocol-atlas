#!/usr/bin/env python3
"""Write into each client-to-server fiche the Lua binding that sends it and how the UI calls it.

From client/symbols/<build>/sender-bindings.yaml: a `client_binding:` block with the
binding's name (and aliases), its function RVA and up to six UI call sites with the
arguments as written there. Documentary (L3 for the binding, L2 for the calls): the
fields are not renamed by this step. Replaced in place on every run.

  python3 tools/codegen/merge_bindings.py --build <id>
"""

import argparse
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BLOCK = re.compile(r"^client_binding:.*?(?=^\S)", re.M | re.S)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--build", required=True)
    args = parser.parse_args()
    symbols = f"client/symbols/{args.build}"
    with open(os.path.join(ROOT, symbols, "sender-bindings.yaml"), encoding="utf-8") as handle:
        table = yaml.safe_load(handle)["senders"]
    table = {(int(k, 16) if isinstance(k, str) else int(k)): v for k, v in table.items()}
    directory = os.path.join(ROOT, "protocol", "opcodes")
    written = 0
    for filename in sorted(os.listdir(directory)):
        if not filename.endswith(".yaml"):
            continue
        opcode = int(filename.split("-", 1)[0], 16)
        entry = table.get(opcode)
        if not entry:
            continue
        path = os.path.join(directory, filename)
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        lines = [f"client_binding:   # the Lua binding whose function sends this packet ({symbols}/sender-bindings.yaml, L3) and the UI's calls (L2)",
                 f"  name: {entry['binding']}",
                 f"  function_rva: \"{entry['function_rva']}\""]
        if entry.get("aliases"):
            lines.append(f"  aliases: [{', '.join(entry['aliases'])}]")
        calls = entry.get("calls") or []
        lines.append("  calls:" if calls else "  calls: []   # no call in the stock UI corpus")
        for call in calls:
            args_repr = ", ".join('"' + str(a).replace('"', "'") + '"' for a in call["args"])
            lines.append(f"    - {{file: \"{call['file']}\", line: {call['line']}, args: [{args_repr}]}}")
        block = "\n".join(lines) + "\n"
        updated = BLOCK.sub(lambda _: block + "\n", text, count=1) if BLOCK.search(text) else text.replace("provenance:", block + "\nprovenance:", 1)
        if updated != text:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(updated)
        written += 1
    print(f"client_binding written into {written} fiches")
    return 0


if __name__ == "__main__":
    sys.exit(main())
