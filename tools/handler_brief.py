#!/usr/bin/env python3
"""Everything a reader needs to name one handler's fields, on one screen.

For each opcode: the fiche's layout (widths), what the handler fires (format, helper),
the Lua arguments the UI declares, the strings the handler references, the server's
writer if the CoA server sends it, and the decompiled lines that read the packet or fire
the event (from build/ghidra/handlers-c, written by DumpC.java). A naming aid, not a
source: the fiche cites the handler RVA and the decompilation, never this script.

  tools/handler_brief.py 0x0593 0x0595 ...
  tools/handler_brief.py --next 12          # the first 12 skeleton layouts with a fire block
"""

import argparse
import glob
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CDIR = os.path.join(ROOT, "build", "ghidra", "handlers-c")
with open(os.path.join(ROOT, "client", "server-layouts.yaml"), encoding="utf-8") as _handle:
    SERVER = {(int(k, 16) if isinstance(k, str) else int(k)): v for k, v in (yaml.safe_load(_handle)["opcodes"] or {}).items()}
INTERESTING = re.compile(r"in_stack_00000010|\+ 0x14\)|FUN_100d3680|FUN_10278c90|FUN_100b9[0-9a-f]{3}|FUN_100e09f0|"
                         r"FUN_100d0a50|FUN_1025a6c0|FUN_100eafb0|DAT_10bc93b8|s_[A-Z][A-Z0-9_]+_10b|\"%|"
                         r"while|for \(|do \{|if \(")


def brief(path, lines_limit):
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    fiche = yaml.safe_load(text)
    print(f"=== {fiche['id']:#06x} {fiche['name']}  [{fiche['status']}]  {os.path.basename(path)}")
    for index, field in enumerate(fiche.get("layout") or []):
        print(f"    layout[{index}] {field.get('name')}: {field.get('type')}" + (f"  repeat={field.get('repeat')}" if "repeat" in field else ""))
    for fire in fiche.get("client_fire") or []:
        print(f"    fire: {fire.get('event')} {fire.get('format')} via {fire.get('helper')} {fire.get('fields') or fire.get('read_slots') or ''}")
    for event in fiche.get("client_events") or []:
        print(f"    lua : {event['event']}({', '.join(event['args'])})  {event['source']}")
    strings = [s for s in (fiche.get("client_strings") or []) if not re.match(r"^[A-Z][A-Z0-9_]+$", s)]
    if strings:
        print(f"    str : {strings[:8]}")
    server = (fiche.get("used_by_server") or {}).get("files")
    if server:
        print(f"    srv : {server}")
    m = re.search(r"^# server writer: ([^\n]+)", text, re.M)
    if m:
        print(f"    srv : {m.group(1)}")
    binding = fiche.get("client_binding")
    if binding:
        print(f"    bind: {binding.get('name')} @ {binding.get('function_rva')}" + (f"  aliases {binding.get('aliases')}" if binding.get('aliases') else ""))
        for call in (binding.get("calls") or [])[:4]:
            print(f"    call: {call.get('file', '').split('/')[-1]}:{call.get('line')} ({', '.join(str(a) for a in call.get('args') or [])})")
    for site in SERVER.get(fiche["id"], []):
        print(f"    srv : {site['file'].split('/')[-1]} -> " + ", ".join(f"{w[0]} {w[1][:22]}" for w in site["writes"]) + f"  [{site['verdict']}]")
    cpath = os.path.join(CDIR, f"{fiche['id']:#06x}.c")
    if os.path.exists(cpath):
        shown = 0
        with open(cpath, encoding="utf-8", errors="replace") as handle:
            for number, line in enumerate(handle, 1):
                if INTERESTING.search(line) and "undefined" not in line[:20]:
                    print(f"    c{number:4}: {line.rstrip()[:150]}")
                    shown += 1
                    if shown >= lines_limit:
                        print("    ...")
                        break
    print()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("opcodes", nargs="*")
    parser.add_argument("--next", type=int)
    parser.add_argument("--lines", type=int, default=40)
    args = parser.parse_args()
    files = sorted(glob.glob(os.path.join(ROOT, "protocol", "opcodes", "*.yaml")))
    if args.next:
        chosen = []
        for path in files:
            fiche = yaml.safe_load(open(path, encoding="utf-8"))
            layout = fiche.get("layout") or []
            if layout and all(str(f.get("name", "")).startswith("field_") for f in layout) and fiche.get("client_fire"):
                chosen.append(path)
            if len(chosen) >= args.next:
                break
    else:
        wanted = {int(o, 16) for o in args.opcodes}
        chosen = [p for p in files if int(os.path.basename(p).split("-", 1)[0], 16) in wanted]
    for path in chosen:
        brief(path, args.lines)
    return 0


if __name__ == "__main__":
    sys.exit(main())
