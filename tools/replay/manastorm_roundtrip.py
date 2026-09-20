#!/usr/bin/env python3
"""Replay: the Manastorm request/result pairs, client to server and back.

    enter    0x0651 (u32 depth)          -> 0x0652 one string, ENTER_MANASTORM_*
    leave    0x0665 (empty)              -> 0x0666 one string, LEAVE_MANASTORM_*
    setslot  0x0689 (u32 slot, u32 spell) -> 0x068A u32 slot, then one string (an error for
                                             a slot the run does not have)

The client's own Lua packet API is the channel (client/lua-packet-api.md): the CoaProbe
addon registers a watch on 0x0652 with `RegisterPacket`, builds a 0x0651 with
`CreatePacket` + `PutUInt32(depth)` and sends it with `CDataStore.Send`, then the probe
log shows the bytes the client received for 0x0652.

What a pass establishes:
  * the server accepts a 4-byte payload for 0x0651 and answers with 0x0652
    (the server's reader: `size must be 4; depth = read<uint32>(0)`);
  * 0x0652 is one NUL-terminated string, and the client's handler receives exactly that
    (the bytes are read back from the CDataStore the handler was given);
  * with `--control`, a 0x0651 of 8 bytes gets NO 0x0652: the size check is real.

What it does not establish: that the client's own sender (FUN_102a68f0, read at L3)
writes those 4 bytes -- the bytes here come from Lua, not from the Manastorm UI.

Preconditions, each checked before anything is concluded:
  * a claimed slot whose containers are running (coa-slot env N);
  * the lab client logged in on a character, CoaProbe answering, and `pkfind` locating
    CreatePacket, RegisterPacket and Send.

Usage:
    python3 tools/replay/manastorm_roundtrip.py --slot 1 [--pair enter|leave|setslot|all] [--control]
"""

import argparse
import json
import shutil
import subprocess
import sys
import time

WATCH_BYTES = 48
# name: (cmsg, fields, smsg, leading u32 expected or None, string prefix, control fields)
PAIRS = {
    "enter": (0x0651, ["u32:1"], 0x0652, None, "ENTER_MANASTORM_", ["u32:1", "u32:0"]),
    "leave": (0x0665, [], 0x0666, None, "LEAVE_MANASTORM_", ["u32:0"]),
    "setslot": (0x0689, ["u32:99", "u32:0"], 0x068A, 99, "", ["u32:99"]),
}


class Inconclusive(Exception):
    """The experiment could not run. Not a verdict on the hypothesis."""


def run(command):
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise Inconclusive(f"{' '.join(command)} failed: "
                           f"{result.stderr.strip() or result.stdout.strip()}")
    return result.stdout


def need(binary):
    if not shutil.which(binary):
        raise Inconclusive(f"{binary} not on PATH")


def probe(*words):
    raw = run(["coa-client-lab", "probe", *[str(w) for w in words]])
    try:
        answer = json.loads(raw)
    except json.JSONDecodeError:
        raise Inconclusive(f"probe did not return JSON: {raw[:200]!r}")
    if answer.get("error"):
        raise Inconclusive(f"probe {words[0]}: {answer['error']}")
    return answer


def last_packet(opcode):
    """The newest log entry of kind packet for `opcode`, or None."""
    entries = probe("log", 40)["result"]["entries"]
    for entry in reversed(entries):
        if entry.get("kind") == "packet" and entry.get("opcode") == opcode:
            return entry
    return None


def cstring(hex_bytes, offset=0):
    raw = bytes.fromhex(hex_bytes)[offset:]
    end = raw.find(b"\0")
    return raw[: end if end >= 0 else len(raw)].decode("ascii", "replace"), end


def replay(name, control):
    cmsg, fields, smsg, leading, prefix, control_fields = PAIRS[name]
    before = last_packet(smsg)
    probe("pkwatch", smsg, WATCH_BYTES)
    sent = probe("pksend", cmsg, *fields)
    print(f"[{name}] sent 0x{cmsg:04X} {fields or 'empty'} at {sent['time']}")
    time.sleep(2)
    after = last_packet(smsg)
    if after is None or after == before:
        print(f"[{name}] FAIL: no 0x{smsg:04X} received")
        return False
    offset = 0
    if leading is not None:
        value = int.from_bytes(bytes.fromhex(after["hex"])[:4], "little")
        print(f"[{name}] received 0x{smsg:04X}: leading u32 = {value}")
        if value != leading:
            print(f"[{name}] FAIL: expected the leading u32 to echo {leading}")
            return False
        offset = 4
    text, end = cstring(after["hex"], offset)
    print(f"[{name}] received 0x{smsg:04X}: {after['read']} bytes read, string {text!r}"
          f" ({'NUL at ' + str(offset + end) if end >= 0 else 'no NUL in the window'})")
    if end < 0 or not text.startswith(prefix) or not text:
        print(f"[{name}] FAIL: 0x{smsg:04X} is not one NUL-terminated {prefix or 'non-empty'}* string")
        return False
    if control:
        sent = probe("pksend", cmsg, *control_fields)
        print(f"[{name}] control: sent 0x{cmsg:04X} {control_fields} at {sent['time']}")
        time.sleep(3)
        if last_packet(smsg) != after:
            print(f"[{name}] FAIL: the server answered a 0x{cmsg:04X} of the wrong size")
            return False
        print(f"[{name}] control: no 0x{smsg:04X} followed -- the size check holds")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--slot", type=int, default=1)
    parser.add_argument("--pair", default="all", choices=["all", *PAIRS])
    parser.add_argument("--control", action="store_true",
                        help="also send each request with the wrong size and require no reply")
    args = parser.parse_args()
    try:
        need("coa-slot")
        need("coa-client-lab")
        run(["coa-slot", "env", str(args.slot)])
        where = probe("pkfind")["result"]["where"]
        for name in ("CreatePacket", "RegisterPacket", "Send"):
            if name not in where:
                raise Inconclusive(f"the client does not expose {name} to Lua")
        print(f"packet API: {where}")
        names = list(PAIRS) if args.pair == "all" else [args.pair]
        results = {name: replay(name, args.control) for name in names}
        print("PASS" if all(results.values()) else "FAIL: " + ", ".join(n for n, ok in results.items() if not ok))
        return 0 if all(results.values()) else 1
    except Inconclusive as problem:
        print(f"INCONCLUSIVE: {problem}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
