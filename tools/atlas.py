#!/usr/bin/env python3
"""Ask the atlas from a shell. Reads protocol/atlas.json (run tools/codegen/coverage.py first).

  tools/atlas.py lookup 0x0726            one fiche: what is known, where it comes from
  tools/atlas.py lookup SMSG_ENTER_MANASTORM_RESULT
  tools/atlas.py search manastorm         names, summaries, events and strings
  tools/atlas.py coverage                 the counts
  tools/atlas.py list --dir c2s --layout unknown --code sender
"""

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load():
    with open(os.path.join(ROOT, "protocol", "atlas.json"), encoding="utf-8") as handle:
        return json.load(handle)["fiches"]


def find(rows, key):
    key = key.strip()
    try:
        opcode = int(key, 0)
        return [r for r in rows if r["id"] == opcode]
    except ValueError:
        return [r for r in rows if r["name"].lower() == key.lower()]


def show(row):
    print(f"{row['hex']} {row['name']}  [{row['direction']}]  status={row['status']} evidence={row['evidence']}")
    print(f"  file:    {row['file']}")
    print(f"  client:  {row['client_code']}" + (f"  handler rva {row['handler_rva']}" if row['handler_rva'] else "")
          + (f"  sender {row['sender']}" if row['sender'] else ""))
    print(f"  layout:  {row['layout_state']}")
    for field in row["layout"]:
        if "repeat" in field:
            print(f"    repeat {field.get('repeat')}: {[f.get('name') for f in field.get('fields', [])]}")
        else:
            print(f"    {field.get('name')}: {field.get('type')} ({field.get('evidence')})")
    if row["fires"]:
        print("  fires:   " + "; ".join(f"{f['event']} {f['format'] or ''}".strip() for f in row["fires"]))
    if row["events"]:
        print("  events:  " + ", ".join(row["events"]))
    if row["used_by_server"]:
        print("  server:  " + ", ".join(row["used_by_server"]))
    if row["replay"]:
        print(f"  replay:  {row['replay']}")
    print(f"  summary: {row['summary']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("lookup").add_argument("key")
    sub.add_parser("search").add_argument("text")
    sub.add_parser("coverage")
    lst = sub.add_parser("list")
    lst.add_argument("--dir", choices=["c2s", "s2c"])
    lst.add_argument("--layout")
    lst.add_argument("--code")
    lst.add_argument("--status")
    args = parser.parse_args()
    rows = load()

    if args.command == "lookup":
        hits = find(rows, args.key)
        if not hits:
            print(f"no fiche for {args.key}")
            return 1
        for row in hits:
            show(row)
    elif args.command == "search":
        text = args.text.lower()
        for row in rows:
            hay = " ".join([row["name"], row["summary"], *row["events"], *row["client_strings"]]).lower()
            if text in hay:
                print(f"{row['hex']} {row['name']:55} {row['layout_state']:8} {row['client_code']}")
    elif args.command == "coverage":
        from collections import Counter
        for key in ("client_code", "layout_state", "status"):
            print(key + ": " + ", ".join(f"{k}={v}" for k, v in sorted(Counter(r[key] for r in rows).items())))
    elif args.command == "list":
        direction = {"c2s": "client_to_server", "s2c": "server_to_client"}.get(args.dir)
        for row in rows:
            if direction and row["direction"] != direction:
                continue
            if args.layout and row["layout_state"] != args.layout:
                continue
            if args.code and row["client_code"] != args.code:
                continue
            if args.status and row["status"] != args.status:
                continue
            print(f"{row['hex']} {row['name']:55} {row['layout_state']:8} {row['client_code']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
