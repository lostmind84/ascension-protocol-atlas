#!/usr/bin/env python3
"""Replay: the Character Advancement vertical and the realm-info packet (roadmap P4).

    credits   0x0926  forge `u8 type, u32 amount`     -> CA_GetCreditAmount(type) answers amount
    realm     0x09BC  forge distinct values           -> GetRealmId / GetRealmExpansion /
                                                         GetRealmAuctionCutRate / GetRealmMaintenance
                                                         read them back from the realm struct
    spec      0x0725  forge `u32 slot, u32 slotCount` -> ASCENSION_CA_SPECIALIZATION_ACTIVE_ID_CHANGED
                                                         fires with slot + 1 (evwatch)
    upload    0x0727  pksend one known-entries record -> the server answers with a fresh 0x0726,
                                                         seen as ASCENSION_KNOWN_ENTRIES_UPDATED
                                                         (evwatch), applied or refused

Server -> client packets are forged with AzerothCore's `.debug send opcode` (opcode.txt in
the worldserver's working directory); the client's answers are read through CoaProbe
(`eval`, `ca`, `evwatch`). Each check prints PASS, FAIL or INCONCLUSIVE and the script's exit
code is 0 only when every selected check passed.

Never `pkwatch` 0x0726 here: `RegisterPacket` REPLACES the native handler for that opcode for
the rest of the client's life (client/lua-packet-api.md), and the flag-gate replay needs it.

Usage:
    python3 tools/replay/ca_vertical.py --slot 1 [--check credits|realm|spec|upload|all]
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

WORLDSERVER_CWD = "/azerothcore"


class Inconclusive(Exception):
    pass


def run(command):
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise Inconclusive(f"{' '.join(command)} failed: {result.stderr.strip() or result.stdout.strip()}")
    return result.stdout


def need(binary):
    if not shutil.which(binary):
        raise Inconclusive(f"{binary} not on PATH")


def worldserver_container(slot):
    for line in run(["coa-slot", "env", str(slot)]).splitlines():
        key, _, value = line.partition("=")
        if key == "WORLDSERVER_CONTAINER":
            return value.strip()
    raise Inconclusive("no worldserver container in coa-slot env")


def forge(container, text):
    with tempfile.TemporaryDirectory() as directory:
        local = os.path.join(directory, "opcode.txt")
        with open(local, "w", encoding="utf-8") as handle:
            handle.write(text)
        run(["docker", "cp", local, f"{container}:{WORLDSERVER_CWD}/opcode.txt"])
    run(["coa-client-lab", "chat", ".debug send opcode"])
    time.sleep(2)


def probe_answer(*words):
    """The probe's whole answer (`result`, `time` in the client's clock). One retry when the
    addon did not answer in time: a /reload right after a forged packet occasionally overruns
    the lab script's 30 s wait, and the retry has always answered."""
    for attempt in (1, 2):
        try:
            raw = run(["coa-client-lab", "probe", *[str(w) for w in words]])
            break
        except Inconclusive as problem:
            if attempt == 2 or "no CoaProbe answer" not in str(problem):
                raise
    try:
        answer = json.loads(raw)
    except json.JSONDecodeError:
        raise Inconclusive(f"probe did not return JSON: {raw[:200]!r}")
    if answer.get("error"):
        raise Inconclusive(f"probe {words[0]}: {answer['error']}")
    return answer


def probe(*words):
    return probe_answer(*words)["result"]


def evaluate(expression):
    return probe("eval", expression)["values"]


def check_credits(container):
    before = evaluate("CA_GetCreditAmount(1)")
    # a value the client does not already hold, so a stale balance from an earlier run cannot pass
    amount = 778 if before == [777] else 777
    forge(container, f"2342 uint8 1 uint32 {amount}\n")
    after = evaluate("CA_GetCreditAmount(1)")
    print(f"[credits] CA_GetCreditAmount(1): {before} -> {after} after 0x0926 (u8 1, u32 {amount})")
    return after == [amount] and after != before


def check_realm(container):
    text = ("2492 uint32 4242 uint32 2 float 0.125 float 0.25 float 0.375 uint32 1 float 0.5 float 0.625 uint32 9 "
            "uint8 1 uint8 0 uint8 0 uint8 0 uint8 0 uint8 0 uint8 0 uint8 0 string alpha string beta uint8 0\n")
    forge(container, text)
    values = evaluate("GetRealmId(), GetRealmExpansion(), GetRealmAuctionCutRate(), GetRealmMaintenance(), GetRealmMaxLevel()")
    print(f"[realm] after 0x09BC: id, expansion, auctionCutRate, maintenance, maxLevel = {values}")
    ok = values[:2] == [4242, 2] and abs(float(values[2]) - 0.5) < 1e-6 and values[3] is True
    return ok


def check_spec(container):
    # GetActiveChrSpec is one of the functions the CoA compat shim overrides, so the event the
    # handler fires is the observation: ASCENSION_CA_SPECIALIZATION_ACTIVE_ID_CHANGED(%u).
    probe("evwatch", "ASCENSION_CA_SPECIALIZATION_ACTIVE_ID_CHANGED")
    forge(container, "1829 uint32 7 uint32 9\n")
    entries = probe("log", 12)["entries"]
    fired = [e for e in entries if e.get("kind") == "event" and e.get("event") == "ASCENSION_CA_SPECIALIZATION_ACTIVE_ID_CHANGED"]
    print(f"[spec] ASCENSION_CA_SPECIALIZATION_ACTIVE_ID_CHANGED after 0x0725 (u32 7, u32 9): {[e.get('args') for e in fired[-2:]]}")
    # measured 2026-09-19: slot 7 -> event 8, slot 2 -> event 3. The event carries slot + 1.
    return bool(fired) and fired[-1].get("args") == [8]


def check_upload(container):
    # The native 0x0726 handler fires ASCENSION_KNOWN_ENTRIES_UPDATED when the set it receives
    # differs from the one it holds (measured 2026-09-19: the server's periodic empty resends
    # fire nothing). So: forge a set with one entry, upload a record the server refuses, and
    # expect the server's answer -- its real, empty set -- to remove the entry and fire the
    # event within seconds of the upload. A pkwatch on 0x0726 would replace that handler.
    probe("evwatch", "ASCENSION_KNOWN_ENTRIES_UPDATED")
    # every probe /reload makes the client upload its own set ~7 s later, answered by an
    # empty 0x0726: let that pass before forging, or it wipes the forged entry
    time.sleep(12)
    forge(container, "1830\nuint32 1\nuint32 6753\nuint32 1\nuint32 1\nuint8 0\nuint32 0\nuint32 0\n")
    time.sleep(3)
    sent = probe_answer("pksend", 0x0727, "u32:1", "u32:31194", "u32:1", "u32:1", "u8:1", "u32:0", "u32:0")
    sent_at = sent["time"]
    time.sleep(3)
    entries = probe("log", 40)["entries"]
    fired = [e.get("time") for e in entries if e.get("kind") == "event"
             and e.get("event") == "ASCENSION_KNOWN_ENTRIES_UPDATED" and e.get("time", 0) >= sent_at]
    system = [e.get("text") for e in entries if e.get("kind") == "system" and e.get("time", 0) >= sent_at]
    state = probe("ca", 6753)
    prompt = [t - sent_at for t in fired if t - sent_at <= 3]
    print(f"[upload] forged 0x0726 with entry 6753, then pksend 0x0727 (one record, entry 31194, rank 1, flag 1) at {sent_at};"
          f" ASCENSION_KNOWN_ENTRIES_UPDATED fired at +{[t - sent_at for t in fired]} s; IsKnownID(6753) -> {state.get('known')};"
          f" system messages since: {system}")
    # proven: the server parses the record (its refusal names the entry) and answers with its own
    # complete set, which replaces the forged one. Whether it APPLIES an accepted record is server
    # policy (ApplyKnownEntriesUpload), not measured. The pksend's own /reload uploads again ~7 s
    # later, so only an event within 3 s is attributed to this upload.
    return bool(prompt) and state.get("known") is False


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--slot", type=int, default=1)
    parser.add_argument("--check", default="all", choices=["all", "credits", "realm", "spec", "upload"])
    args = parser.parse_args()
    try:
        need("coa-slot"); need("coa-client-lab"); need("docker")
        container = worldserver_container(args.slot)
        probe("ping")
        checks = {"credits": lambda: check_credits(container), "realm": lambda: check_realm(container),
                  "spec": lambda: check_spec(container), "upload": lambda: check_upload(container)}
        names = list(checks) if args.check == "all" else [args.check]
        results = {}
        for name in names:
            try:
                results[name] = checks[name]()
                print(f"[{name}] {'PASS' if results[name] else 'FAIL'}")
            except Inconclusive as problem:
                results[name] = None
                print(f"[{name}] INCONCLUSIVE: {problem}")
        if all(results.values()):
            print("PASS")
            return 0
        print("FAIL" if any(v is False for v in results.values()) else "INCONCLUSIVE")
        return 1 if any(v is False for v in results.values()) else 2
    except Inconclusive as problem:
        print(f"INCONCLUSIVE: {problem}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
