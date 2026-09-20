#!/usr/bin/env python3
"""Attach to each fiche the Lua arguments of the events its handler fires.

Joins `client_strings` (the literals the handler references, from its decompilation)
with `client/event-args.yaml` (what the UI's method named after the event receives).
Written as a `client_events:` block, replaced in place on every run. The block says
what Lua sees; whoever names the layout reads it next to the handler's widths.

  python3 tools/codegen/merge_events.py
"""

import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BLOCK = re.compile(r"^client_events:.*?(?=^\S)", re.M | re.S)
EVENT = re.compile(r"^[A-Z][A-Z0-9_]{3,}$")


def main():
    with open(os.path.join(ROOT, "client", "event-args.yaml"), encoding="utf-8") as handle:
        table = yaml.safe_load(handle)
    definitions, corpus = table["definitions"], table["corpus"]

    directory = os.path.join(ROOT, "protocol", "opcodes")
    written = 0
    for filename in sorted(os.listdir(directory)):
        if not filename.endswith(".yaml"):
            continue
        path = os.path.join(directory, filename)
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        fiche = yaml.safe_load(text)
        events = [s for s in (fiche.get("client_strings") or []) if EVENT.match(s) and s in definitions]
        if not events:
            continue
        lines = [f"client_events:   # Lua arguments of the events this handler names (corpus {corpus}, L2)"]
        for event in events:
            for entry in definitions[event]:
                lines.append(f"  - event: {event}")
                lines.append(f"    args: [{', '.join(entry['args'])}]")
                lines.append(f"    source: \"{entry['sources'][0]}\"")
        block = "\n".join(lines) + "\n"
        if BLOCK.search(text):
            updated = BLOCK.sub(lambda _: block + "\n", text, count=1)
        else:
            updated = text.replace("provenance:", block + "\nprovenance:", 1)
        if updated != text:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(updated)
            written += 1
    print(f"client_events written into {written} fiches")
    return 0


if __name__ == "__main__":
    sys.exit(main())
