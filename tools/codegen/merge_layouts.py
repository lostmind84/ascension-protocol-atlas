#!/usr/bin/env python3
"""Merge recovered field sequences into the stub fiches.

`packet_layout.py` recovers the widths a handler reads, in order. This writes them into
the matching fiche's `layout`, but only into fiches nobody has worked on yet: a stub still
at `status: unknown` with an empty layout. Anything a human has touched is left alone.

Fields are named `field_0`, `field_1`, ... on purpose. The extraction knows the width and
the order and nothing else; inventing names would dress a width up as a meaning.

It also cannot see structure. A packet that is a count followed by a repeated record comes
out flat — `0x0726` reads as seven fields, which is its `u32 count` plus one record's six.
Each merged fiche says so.

  python3 tools/codegen/merge_layouts.py --build <id> [--dry-run]
"""

import argparse
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STUB_LAYOUT = "layout: []   # unknown"
MARKER = "# Widths and order, read out of the handler at"
GENERATED = re.compile(
    r"^layout:\n(?:  - name: field_\d+\n    type: \w+\n    evidence: L3\n)+"
    r"# Widths and order[^\n]*\n(?:#[^\n]*\n)*", re.M)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--build", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    symbols = f"client/symbols/{args.build}"
    with open(os.path.join(ROOT, symbols, "layouts.yaml"), encoding="utf-8") as handle:
        recovered = yaml.safe_load(handle)["layouts"]
    recovered = {(int(k, 16) if isinstance(k, str) else int(k)): v
                 for k, v in recovered.items()}

    directory = os.path.join(ROOT, "protocol", "opcodes")
    merged = skipped = absent = cleared = 0
    for filename in sorted(os.listdir(directory)):
        # Handler layouts are server-to-client. The client-to-server fiches belong to
        # merge_senders.py; touching them here made the two merges fight over the same
        # block and re-insert provenance on every regeneration.
        if not filename.endswith(".yaml") or "-cmsg-" in filename:
            continue
        path = os.path.join(directory, filename)
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        opcode = int(filename.split("-", 1)[0], 16)
        entry = recovered.get(opcode)
        if "status: unknown" not in text:
            skipped += 1                      # someone has written into this one
            continue
        if entry is None:
            # A layout this tool wrote earlier, for an opcode the extractor no longer
            # recovers, is stale evidence and has to go -- an earlier run with a looser
            # string rule left phantom layouts behind, and nothing else clears them.
            if GENERATED.search(text):
                updated = GENERATED.sub(STUB_LAYOUT + "\n", text, count=1)
                updated = updated.replace(
                    "  - level: L3\n"
                    f"    source: \"{symbols}/layouts.yaml (handler read sequence)\"\n"
                    "    claim: \"the field widths and their order\"\n", "", 1)
                if not args.dry_run:
                    with open(path, "w", encoding="utf-8") as handle:
                        handle.write(updated)
                cleared += 1
            absent += 1
            continue
        if STUB_LAYOUT not in text and not GENERATED.search(text):
            skipped += 1
            continue

        lines = ["layout:"]
        for index, kind in enumerate(entry["fields"]):
            lines.append(f"  - name: field_{index}")
            lines.append(f"    type: {kind}")
            lines.append("    evidence: L3")
        lines += [
            "# Widths and order, read out of the handler at"
            f" {entry['read_in_rva']} by tools/extract/packet_layout.py.",
            "# Names are placeholders and the structure is flat: a count followed by a",
            "# repeated record appears here as the count plus one record's fields.",
        ]
        block = "\n".join(lines)
        if STUB_LAYOUT in text:
            updated = text.replace(STUB_LAYOUT, block, 1)
            updated = updated.replace(
                "provenance:",
                "provenance:\n  - level: L3\n"
                f"    source: \"{symbols}/layouts.yaml (handler read sequence)\"\n"
                "    claim: \"the field widths and their order\"", 1)
        else:
            updated = GENERATED.sub(block + "\n", text, count=1)   # refresh in place
        if not args.dry_run:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(updated)
        merged += 1

    print(f"merged: {merged}")
    print(f"skipped (already worked on): {skipped}")
    print(f"no recovered layout: {absent} (stale generated layouts cleared: {cleared})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
