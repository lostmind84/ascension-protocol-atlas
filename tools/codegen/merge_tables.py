#!/usr/bin/env python3
"""Write the result-code tables into the fiches as `client_enums:`.

From client/symbols/<build>/result-tables.yaml (the string tables a handler indexes by a
value read from the packet). When the indexing variable is one of the handler's reads
(handler-fire.yaml), the block names the field; otherwise it just lists the values.
Replaced in place on every run.

  python3 tools/codegen/merge_tables.py --build <id>
"""

import argparse
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BLOCK = re.compile(r"^client_enums:.*?(?=^\S)", re.M | re.S)


def as_map(mapping):
    return {(int(k, 16) if isinstance(k, str) else int(k)): v for k, v in (mapping or {}).items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--build", required=True)
    args = parser.parse_args()
    symbols = f"client/symbols/{args.build}"
    with open(os.path.join(ROOT, symbols, "result-tables.yaml"), encoding="utf-8") as handle:
        tables = as_map(yaml.safe_load(handle)["tables"])
    with open(os.path.join(ROOT, symbols, "handler-fire.yaml"), encoding="utf-8") as handle:
        fire = as_map(yaml.safe_load(handle)["handlers"])

    directory = os.path.join(ROOT, "protocol", "opcodes")
    written = 0
    for filename in sorted(os.listdir(directory)):
        if not filename.endswith(".yaml"):
            continue
        opcode = int(filename.split("-", 1)[0], 16)
        if opcode not in tables:
            continue
        path = os.path.join(directory, filename)
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        def flatten(entries):
            for read in entries:
                if isinstance(read, dict) and "repeat" in read:
                    yield from flatten(read["reads"])
                else:
                    yield read
        reads = list(flatten((fire.get(opcode) or {}).get("reads") or []))
        read_index = {(r[0] if isinstance(r, list) else r["var"]): k for k, r in enumerate(reads)}
        layout = yaml.safe_load(text).get("layout") or []
        lines = [f"client_enums:   # string tables the handler indexes by a packet value ({symbols}/result-tables.yaml, L3)"]
        for table in tables[opcode]:
            k = read_index.get(table.get("index_var"))
            field = layout[k]["name"] if k is not None and k < len(layout) and "repeat" not in layout[k] else None
            lines.append(f"  - field: {field or 'null'}   # value i means values[i]; the handler checks i < {table['count']}")
            lines.append(f"    table_va: \"{table['table_va']}\"")
            lines.append("    values: [" + ", ".join(v for v in table["values"]) + "]")
        block = "\n".join(lines) + "\n"
        updated = BLOCK.sub(lambda _: block + "\n", text, count=1) if BLOCK.search(text) else text.replace("provenance:", block + "\nprovenance:", 1)
        if updated != text:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(updated)
        written += 1
    print(f"client_enums written into {written} fiches")
    return 0


if __name__ == "__main__":
    sys.exit(main())
