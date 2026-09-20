#!/usr/bin/env python3
"""Write into each SMSG_PATCH_* fiche which client DBC table its row goes into.

From client/symbols/<build>/patch-tables.yaml: a `patches_table:` block (dbc, table
instance, record size and field count from the dataset manifest), and, when the layout's
first field is a block copy of exactly the record size, that field is named `row` with a
note. The claim is the binary's (L3); the record size is the dataset's (L2). Only stubs
are touched; replaced in place on every run.

  python3 tools/codegen/merge_patch.py --build <id>
"""

import argparse
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BLOCK = re.compile(r"^patches_table:.*?(?=^\S)", re.M | re.S)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--build", required=True)
    args = parser.parse_args()
    symbols = f"client/symbols/{args.build}"
    with open(os.path.join(ROOT, symbols, "patch-tables.yaml"), encoding="utf-8") as handle:
        table = yaml.safe_load(handle)
    dataset = table["dataset"]
    bound = {(int(k, 16) if isinstance(k, str) else int(k)): v for k, v in table["handlers"].items()}

    directory = os.path.join(ROOT, "protocol", "opcodes")
    written = rows = 0
    for filename in sorted(os.listdir(directory)):
        if not filename.endswith(".yaml"):
            continue
        opcode = int(filename.split("-", 1)[0], 16)
        if opcode not in bound:
            continue
        path = os.path.join(directory, filename)
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        fiche = yaml.safe_load(text)
        entries = bound[opcode]
        lines = [f"patches_table:   # the client DBC table this packet writes a row into ({symbols}/patch-tables.yaml, L3; sizes from {dataset}, L2)"]
        for entry in entries:
            lines.append(f"  - dbc: {entry['dbc']}")
            lines.append(f"    instance: \"{entry['instance']}\"   # the DLL's table object in .data; rows at +0x20, minId +0x10, maxId +0xc")
            lines.append(f"    record_size: {entry.get('record_size')}")
            lines.append(f"    fields: {entry.get('fields')}")
        block = "\n".join(lines) + "\n"
        updated = BLOCK.sub(lambda _: block + "\n", text, count=1) if BLOCK.search(text) else text.replace("provenance:", block + "\nprovenance:", 1)
        layout = fiche.get("layout") or []
        first = layout[0] if layout else None
        size = entries[0].get("record_size")
        if (fiche.get("status") == "unknown" and first and str(first.get("name", "")).startswith("field_")
                and str(first.get("type")) == f"bytes_{size}" and len(entries) == 1):
            updated = re.sub(rf"^  - name: {first['name']}\n    type: bytes_{size}\n",
                             f"  - name: row\n    type: bytes_{size}\n    notes: \"one row of {entries[0]['dbc']} ({entries[0]['fields']} fields of 4 bytes), as the client's table stores it; the strings that follow are the row's string columns, inline\"\n",
                             updated, count=1, flags=re.M)
            updated = updated.replace("status: unknown", "status: hypothetical", 1)
            prov = ("  - level: L3\n"
                    f"    source: \"{symbols}/patch-tables.yaml (CustomDBCMgr load idiom and the handler's table object)\"\n"
                    f"    claim: \"the packet carries one row of {entries[0]['dbc']} into the client's copy of that table\"\n")
            if prov not in updated:
                updated = updated.replace("provenance:\n", "provenance:\n" + prov, 1)
            rows += 1
        if updated != text:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(updated)
        written += 1
    print(f"patches_table written into {written} fiches; {rows} block copies named as the table row")
    return 0


if __name__ == "__main__":
    sys.exit(main())
