#!/usr/bin/env python3
"""Lend the server's operand names to a skeleton layout whose widths the server agrees with.

From client/server-layouts.yaml: when a site's verdict is `agree` or `agree-where-visible`
(one server write per client read, same widths), each `field_N` takes the identifier of
the server's operand -- `uint32(challengeID)` gives `challengeID`, `data << level` gives
`level`; a literal (`uint32(0)`) or an expression without a plain identifier keeps its
placeholder. Only stubs (`status: unknown`) are touched. The name is the fork's, so it is
graded L1 in provenance; the width stays the client's L3.

  python3 tools/codegen/merge_server_names.py
"""

import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
IDENT = re.compile(r"^(?:u?int(?:8|16|32|64)|float|double|static_cast<[^>]+>)?\s*\(?\s*([A-Za-z_]\w*(?:\.\w+|->\w+)*)\s*\)?$")


def name_of(code, comment):
    m = IDENT.match(code.strip())
    if m:
        ident = m.group(1).split("->")[-1].split(".")[-1]
        if ident not in ("uint8", "uint16", "uint32", "uint64", "float", "size") and not ident.isdigit():
            return ident
    if comment:
        words = re.findall(r"[A-Za-z_]\w*", comment)
        if words and len(words) <= 3:
            return "_".join(w.lower() for w in words)
    return None


def main():
    with open(os.path.join(ROOT, "client", "server-layouts.yaml"), encoding="utf-8") as handle:
        table = yaml.safe_load(handle)["opcodes"] or {}
    table = {(int(k, 16) if isinstance(k, str) else int(k)): v for k, v in table.items()}
    directory = os.path.join(ROOT, "protocol", "opcodes")
    named = 0
    for filename in sorted(os.listdir(directory)):
        if not filename.endswith(".yaml"):
            continue
        opcode = int(filename.split("-", 1)[0], 16)
        sites = [s for s in table.get(opcode, []) if str(s.get("verdict", "")).startswith("agree") and "by-size" not in str(s.get("verdict"))]
        if not sites:
            continue
        path = os.path.join(directory, filename)
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        fiche = yaml.safe_load(text)
        layout = fiche.get("layout") or []
        if fiche.get("status") != "unknown" or not layout or not all(str(f.get("name", "")).startswith("field_") for f in layout if "repeat" not in f):
            continue
        writes = [w for w in sites[0]["writes"] if w[0] != "cstring"]
        flat = [f for f in layout if "repeat" not in f]
        if len(writes) != len(flat):
            continue
        used, changed = set(), False
        for index, (write, field) in enumerate(zip(writes, flat)):
            kind, code = write[0], write[1]
            comment = ""
            name = name_of(code, comment)
            if not name or name in used:
                continue
            used.add(name)
            text = re.sub(rf"^  - name: {field['name']}\n", f"  - name: {name}\n", text, count=1, flags=re.M)
            changed = True
        if not changed:
            continue
        text = text.replace("status: unknown", "status: hypothetical", 1)
        note = (f"# Names: lent by the CoA server's writer in {sites[0]['file']} (L1), whose widths agree with the\n"
                "# client's reads position by position; a field the server writes as a literal keeps its placeholder.\n")
        if note not in text:
            text = re.sub(r"^(# Widths and order[^\n]*\n)", lambda m: m.group(1) + note, text, count=1, flags=re.M)
        prov = ("  - level: L1\n"
                f"    source: \"{sites[0]['file']} (the CoA server's writer, client/server-layouts.yaml)\"\n"
                "    claim: \"the field names\"\n")
        if prov not in text:
            text = text.replace("provenance:\n", "provenance:\n" + prov, 1)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        named += 1
    print(f"server names lent to {named} fiches")
    return 0


if __name__ == "__main__":
    sys.exit(main())
