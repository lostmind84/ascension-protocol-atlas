#!/usr/bin/env python3
"""Replay: what does `SMSG 0x0726` actually drive in the client?

The experiment `azerothcore-wotlk-coa#4027` never ran. It shipped the packet with its u8
field written as 0 and its entries were ignored in game; `#4128` concluded the client
requires that byte to be 1 before `IsKnownID` answers yes.

Run against a real client, that is not what happens:

    empty set (count=0)      ->  IsKnownID(entry) false      -- the set is replaced wholesale
    one record, u8 = 0       ->  IsKnownID true, IsLockedID false
    one record, u8 = 1       ->  IsKnownID true, IsLockedID true

Presence in the set is what makes an entry known. The u8 gates `IsLockedID`, and a locked
entry is one the UI will not let the player interact with -- which looks like "the entry
did not work" without being the same thing.

No server code is needed. AzerothCore already ships a generic packet forge:
`.debug send opcode` (RBAC_PERM_COMMAND_DEBUG) reads `opcode.txt` from the worldserver's
working directory and sends the packet it describes to the commanding player. In the slot
containers that directory is `/azerothcore`, so the file goes in with `docker cp`.

Preconditions, each checked before anything is concluded:
  * a claimed slot whose worldserver container is running
  * the lab client logged in, on a character, with an account holding the DEBUG permission
  * the lab client running the STOCK patch-B.MPQ -- the CoA patch's
    CharacterAdvancementCompat.lua overrides C_CharacterAdvancement, and the run would
    measure the shim instead of the wire (ADR 0007). The probe reports `shim`; this
    script refuses to conclude when it is set.

Usage:
    python3 tools/replay/0x0726_flag_gate.py --slot 1 [--entry 31194] [--dry-run]
"""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import os

OPCODE = 0x0726
WORLDSERVER_CWD = "/azerothcore"


class Inconclusive(Exception):
    """The experiment could not run. Not a verdict on the hypothesis."""


def run(command, **kwargs):
    result = subprocess.run(command, capture_output=True, text=True, **kwargs)
    if result.returncode != 0:
        raise Inconclusive(f"{' '.join(command)} failed: "
                           f"{result.stderr.strip() or result.stdout.strip()}")
    return result.stdout


def need(binary):
    if not shutil.which(binary):
        raise Inconclusive(f"{binary} not on PATH")


def worldserver_container(slot):
    need("coa-slot")
    for line in run(["coa-slot", "env", str(slot)]).splitlines():
        key, _, value = line.partition("=")
        if key == "WORLDSERVER_CONTAINER":
            return value.strip()
    raise Inconclusive(f"coa-slot env {slot} did not name a worldserver container")


def packet_text(entry, rank, marker, flag, build_time, reserved):
    """`.debug send opcode`'s format: decimal opcode, then <type> <value> pairs.

    The record layout is the fiche's: u32 count, then per record u32 entryId, u32 rank,
    u32 marker, u8 flag, u32 buildTime, u32 reserved.
    """
    return "\n".join([
        f"{OPCODE}",
        "uint32 1",
        f"uint32 {entry}",
        f"uint32 {rank}",
        f"uint32 {marker}",
        f"uint8 {flag}",
        f"uint32 {build_time}",
        f"uint32 {reserved}",
        "",
    ])


def deliver(container, text, dry_run):
    if dry_run:
        print("  opcode.txt would be:")
        print("".join(f"    {line}\n" for line in text.splitlines()))
        return
    need("docker")
    with tempfile.TemporaryDirectory() as directory:
        local = os.path.join(directory, "opcode.txt")
        with open(local, "w", encoding="utf-8") as handle:
            handle.write(text)
        run(["docker", "cp", local, f"{container}:{WORLDSERVER_CWD}/opcode.txt"])


def probe_ca(entry):
    need("coa-client-lab")
    raw = run(["coa-client-lab", "probe", "ca", str(entry)])
    try:
        answer = json.loads(raw)
    except json.JSONDecodeError:
        raise Inconclusive(f"probe did not return JSON: {raw[:200]!r}")
    result = answer.get("result", answer)
    if result.get("shim"):
        # The CoA compat shim overrides only GetActiveChrSpec, SwitchActiveChrSpec,
        # CanSwitchActiveChrSpec, GetEntriesByClass, GetEntryByInternalID and
        # GetPendingRankByEntryID -- measured by grepping both Compat files. IsKnownID and
        # GetTalentRankByID are NOT among them, so this experiment still reads the native
        # container. Reported, not refused.
        print("  note: CoA compat shim loaded; IsKnownID and GetTalentRankByID are not "
              "among the functions it overrides")
    if "known" not in result:
        raise Inconclusive("the probe could not answer IsKnownID: "
                           f"{result.get('unavailable', result)}")
    return result


def observe(container, entry, flag, dry_run, empty=False):
    label = "an empty set" if empty else f"one record with u8={flag}"
    print(f"forging 0x{OPCODE:04X} as {label} for entry {entry}")
    text = f"{OPCODE}\nuint32 0\n" if empty else packet_text(entry, 1, 1, flag, 0, 0)
    deliver(container, text, dry_run)
    if dry_run:
        return None
    need("coa-client-lab")
    run(["coa-client-lab", "chat", ".debug send opcode"])
    result = probe_ca(entry)
    print(f"  IsKnownID -> {result['known']}, IsLockedID -> {result.get('locked')},"
          f" rank -> {result.get('rank')}")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--slot", type=int, default=1)
    parser.add_argument("--entry", type=int, default=31194,
                        help="entry to test (default 31194: present in both registered "
                             "data snapshots, and #4128's worked example)")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the packet without sending it")
    args = parser.parse_args()

    try:
        container = "<worldserver>" if args.dry_run else worldserver_container(args.slot)
        empty = observe(container, args.entry, 0, args.dry_run, empty=True)
        zero = observe(container, args.entry, 0, args.dry_run)
        one = observe(container, args.entry, 1, args.dry_run)
    except Inconclusive as reason:
        print(f"\nINCONCLUSIVE: {reason}", file=sys.stderr)
        return 2

    if args.dry_run:
        print("dry run: nothing was sent, no conclusion")
        return 2

    checks = [
        ("an empty set clears the container", empty["known"] is False),
        ("a record makes the entry known with u8=0", zero["known"] is True),
        ("a record makes the entry known with u8=1", one["known"] is True),
        ("u8=0 leaves the entry unlocked", zero.get("locked") is False),
        ("u8=1 locks the entry", one.get("locked") is True),
    ]
    print()
    for label, ok in checks:
        print(f"  {'ok  ' if ok else 'FAIL'} {label}")
    if all(ok for _, ok in checks):
        print("\nPASS: 0x0726 replaces the known-entries set; presence drives IsKnownID"
              " and the u8 drives IsLockedID")
        return 0
    print("\nFAIL: the client did not behave as recorded", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
