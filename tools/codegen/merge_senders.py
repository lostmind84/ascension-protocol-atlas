#!/usr/bin/env python3
"""Merge recovered client-side sender layouts into the client-to-server stub fiches.

Same rules as merge_layouts.py: only fiches nobody has worked on (`status: unknown` with
an empty or previously generated layout) are touched; a generated block is refreshed in
place; a stale block for an opcode the extractor no longer recovers is reset to the stub.
`via_helper` senders are merged with a note that the layout is a prefix at best.

  python3 tools/codegen/merge_senders.py --build <id>
"""

import argparse
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STUB_LAYOUT = "layout: []   # unknown"
GENERATED = re.compile(
    r"^layout:(?: \[\])?\n(?:  - name: field_\d+\n    type: (?:[\w\[\]]+|\{None: None\})\n    evidence: L3\n)*"
    r"# Widths and order, read out of the client's sender[^\n]*\n(?:#[^\n]*\n)*", re.M)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--build", required=True)
    args = parser.parse_args()

    symbols = f"client/symbols/{args.build}"
    with open(os.path.join(ROOT, symbols, "senders.yaml"), encoding="utf-8") as handle:
        recovered = yaml.safe_load(handle)["senders"]
    recovered = {(int(k, 16) if isinstance(k, str) else int(k)): v for k, v in recovered.items()}

    directory = os.path.join(ROOT, "protocol", "opcodes")
    merged = skipped = cleared = 0
    provenance = ("  - level: L3\n"
                  f"    source: \"{symbols}/senders.yaml (client sender PutData sequence)\"\n"
                  "    claim: \"the field widths and their order, as the client writes them\"\n")
    for filename in sorted(os.listdir(directory)):
        if not filename.endswith(".yaml") or "-cmsg-" not in filename:
            continue
        path = os.path.join(directory, filename)
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        if "status: unknown" not in text:
            skipped += 1
            continue
        opcode = int(filename.split("-", 1)[0], 16)
        entry = recovered.get(opcode)
        if entry is None:
            if GENERATED.search(text):
                text = GENERATED.sub(STUB_LAYOUT + "\n", text, count=1).replace(provenance, "", 1)
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(text)
                cleared += 1
            continue
        if STUB_LAYOUT not in text and not GENERATED.search(text):
            skipped += 1
            continue
        lines = ["layout:" + (" []" if not entry["fields"] else "")]
        for index, kind in enumerate(entry["fields"]):
            lines += [f"  - name: field_{index}", f"    type: {kind}", "    evidence: L3"]
        lines.append(f"# Widths and order, read out of the client's sender at {entry['sender_site_rva']}"
                     " by tools/extract/client_sender.py.")
        if entry["via_helper"]:
            lines.append("# A helper is called between the opcode write and the send: this is at best a")
            lines.append("# PREFIX of the payload. An empty list here does not mean an empty packet.")
        elif not entry["fields"]:
            lines.append("# No PutData between the opcode write and the send: the packet is empty.")
        block = "\n".join(lines) + "\n"
        if STUB_LAYOUT in text:
            text = text.replace(STUB_LAYOUT, block.rstrip("\n"), 1)
            if provenance not in text:
                text = text.replace("provenance:", "provenance:\n" + provenance.rstrip("\n"), 1)
        else:
            text = GENERATED.sub(lambda _: block, text, count=1)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        merged += 1
    print(f"merged: {merged}; skipped (worked on): {skipped}; stale cleared: {cleared}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
