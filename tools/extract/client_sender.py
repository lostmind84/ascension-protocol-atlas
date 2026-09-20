#!/usr/bin/env python3
"""Recover what the client WRITES into each client-to-server packet.

Every sender goes through a table of Wow.exe function pointers in .data:

    call [0x10bc90bc]      CDataStore constructor -- a second one means a second packet
    call [0x10bc90cc]      Put(u32) -- the opcode first (`push <opcode>` before it), then
                           any u32 field the sender writes the same way
    call [0x10bc90dc]      PutData(ptr, size) -- the size is the immediate pushed before ptr
    call [0x10bc90d8]      put a string
    call [0x10bc90fc]      CDataStore::Finalize -- the last write is behind us; the send
                           (0x10bc91e8/ec) follows (also reached through FUN_1008e4c0)

So: find `push <opcode>` followed by the Put(u32) call, then read every Put(u32) and
PutData size up to the send. A call to anything else between them means part of the
payload is written by a helper the scan does not follow; the layout is then marked
`via_helper` and is a prefix at best, never the whole packet.

Until 2026-09-19 the scan took 0x10bc90cc for an opcode-only write and stopped at its
second call; every sender with a u32 written that way came out as "no sender found"
(seventeen opcodes). Decompiling those senders (tools/ghidra/scripts/SenderC.java)
showed `(*DAT_10bc90cc)(0x67c); (*DAT_10bc90cc)((int)fVar2);` -- the same call, a
value, not an opcode. A layout that ended before such a call was never emitted, so no
earlier recovered layout was wrong; they were missing.

Validated against twelve senders read by hand (client/client-senders.md).

  python3 tools/extract/client_sender.py <Extensions.dll> --build <id> --out <file>
"""

import argparse
import hashlib
import os
import re
import struct
import subprocess
import sys
import importlib.util

import yaml

CTOR, OPCODE_WRITE, PUT_DATA, PUT_STRING, SEND = "0x10bc90bc", "0x10bc90cc", "0x10bc90dc", "0x10bc90d8", "0x10bc90fc"
# Two helpers wrap the same calls (decompiled: client/client-senders.md):
#   FUN_1008d690(store, opcode)  constructs the CDataStore and writes the opcode -- the
#                                 caller then PutDatas the payload and sends;
#   FUN_100e08b0(opcode)         constructs, writes the opcode and sends: an EMPTY packet.
BEGIN_HELPER, SEND_EMPTY_HELPER, SEND_HELPER = "0x1008d690", "0x100e08b0", "0x1008e4c0"
PUSH_IMM = re.compile(r"^push\s+0x([0-9a-f]+)$")
MOV_IMM = re.compile(r"^mov\s+e[a-z]{2},0x([0-9a-f]+)$")
CALL_PTR = re.compile(r"^call\s+DWORD PTR ds:(0x10bc90[0-9a-f]{2})$")
CALL_DIRECT = re.compile(r"^call\s+0x[0-9a-f]+$")
TYPE = {1: "u8", 2: "u16", 4: "u32", 8: "u64"}


def load_image(path):
    spec = importlib.util.spec_from_file_location(
        "opcode_names", os.path.join(os.path.dirname(os.path.abspath(__file__)), "opcode_names.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Image(path)


def disassemble(image, rva, length, scratch):
    offset = image.offset(image.base + rva)
    with open(scratch, "wb") as handle:
        handle.write(image.data[offset:offset + length])
    out = subprocess.run(["objdump", "-D", "-b", "binary", "-m", "i386", "-M", "intel",
                          f"--adjust-vma={image.base + rva:#x}", scratch],
                         capture_output=True, text=True).stdout
    return [line.split("\t")[-1].strip() for line in out.splitlines() if ":\t" in line]


def push_sites(image, opcodes):
    """Where an opcode is loaded as an immediate: `push imm32` or `mov r32, imm32`."""
    data = image.data
    _, rva, _, raw, rsize = next(s for s in image.sections if s[0] == ".text")
    sites = {}
    for offset in range(raw, raw + rsize - 5):
        if data[offset] == 0x68 or 0xB8 <= data[offset] <= 0xBF:
            value = struct.unpack_from("<I", data, offset + 1)[0]
            if value in opcodes:
                sites.setdefault(value, []).append(rva + (offset - raw))
    return sites


def collapse(fields):
    """`PutData(&len, 4)` then `PutData(ptr, len)` -- a u32 whose next PutData has a computed
    size -- is the client's length-prefixed string (SenderC.java on 0x05a4, 0x05a9, 0x05ad,
    0x05bf, 0x05c9: `dc &local,4` then `dc ptr,local`). One `lpstring`, not `u32, unknown`."""
    out = []
    for kind in fields:
        if kind == "unknown" and out and out[-1] == "u32":
            out[-1] = "lpstring"
        else:
            out.append(kind)
    return out


def read_sender(image, site, opcode, scratch):
    """Field widths written between the opcode write and the send, or None if no send."""
    listing = disassemble(image, site, 0x800, scratch)
    started, pushes, fields, helper = False, [], [], False
    for text in listing:
        push = PUSH_IMM.match(text) or MOV_IMM.match(text)
        if push:
            pushes.append(int(push.group(1), 16))
            if len(pushes) > 4:
                pushes = pushes[-4:]
            continue
        if text.startswith("push"):
            pushes.append(None)
            if len(pushes) > 4:
                pushes = pushes[-4:]
            continue
        call = CALL_PTR.match(text)
        if call:
            target = call.group(1)
            if target == OPCODE_WRITE:
                if not started and opcode in pushes:
                    started = True
                elif started:
                    fields.append("u32")   # Put(u32): the same call that wrote the opcode
            elif started and target == CTOR:
                break                # a second packet begins; stop
            elif started and target == PUT_DATA:
                # (ptr, size): size is the immediate before the pointer push
                immediates = [p for p in pushes[-2:] if p is not None]
                width = immediates[0] if immediates else None
                # `?` is YAML's complex-key marker and round-trips as a dict; say `unknown`.
                fields.append(TYPE.get(width, f"bytes_{width}") if width else "unknown")
            elif started and target == PUT_STRING:
                fields.append("cstring")
            elif started and target == SEND:
                return collapse(fields), helper
            pushes = []
            continue
        if CALL_DIRECT.match(text):
            target = text.split()[-1]
            if not started and opcode in pushes and target == BEGIN_HELPER:
                started = True
                pushes = []
                continue
            if not started and opcode in pushes and target == SEND_EMPTY_HELPER:
                return [], False
            if started and target == SEND_HELPER:
                return collapse(fields), helper
            if started:
                helper = True
        if text == "int3" or text.startswith("ret"):
            if started:
                break
    return None, helper


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("dll")
    parser.add_argument("--build", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--only", type=lambda v: int(v, 0), action="append")
    args = parser.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    with open(os.path.join(root, "client", "symbols", args.build, "opcodes.yaml"), encoding="utf-8") as handle:
        names = yaml.safe_load(handle)["opcodes"]
    names = {(int(k, 16) if isinstance(k, str) else int(k)): v for k, v in names.items()}
    with open(os.path.join(root, "protocol", "known-baseline.yaml"), encoding="utf-8") as handle:
        baseline = yaml.safe_load(handle)["opcodes"]
    baseline = {(int(k, 16) if isinstance(k, str) else int(k)): v for k, v in baseline.items()}

    wanted = set(args.only) if args.only else {
        op for op, name in names.items()
        if name.startswith("CMSG_") and baseline.get(op) != name}
    # unnamed opcodes the server handles as CMSG are worth scanning too
    wanted |= {0x0727}

    image = load_image(args.dll)
    scratch = os.path.join(os.path.dirname(args.out) or ".", ".sender-scratch.bin")
    sites = push_sites(image, wanted)

    results, none = {}, 0
    for opcode in sorted(wanted):
        best = None
        for site in sites.get(opcode, []):
            fields, helper = read_sender(image, site, opcode, scratch)
            if fields is None:
                continue
            candidate = {"sender_site_rva": site, "fields": fields, "via_helper": helper}
            if best is None or len(fields) > len(best["fields"]):
                best = candidate
        if best is None:
            none += 1
            continue
        results[opcode] = best
    if os.path.exists(scratch):
        os.remove(scratch)

    with open(args.out, "w", encoding="utf-8") as out:
        print("# Generated by tools/extract/client_sender.py -- do not hand-edit.", file=out)
        print(f"build: {args.build}", file=out)
        print(f"sha256: {hashlib.sha256(image.data).hexdigest()}", file=out)
        print("# PutData widths between the opcode write and the send, in order. `via_helper`", file=out)
        print("# means a call to something else sat between them, so the payload is at best", file=out)
        print("# a prefix of what is written.", file=out)
        print(f"recovered: {len(results)}", file=out)
        print(f"no_sender_found: {none}", file=out)
        print("senders:", file=out)
        for opcode in sorted(results):
            entry = results[opcode]
            print(f"  {opcode:#06x}:", file=out)
            print(f"    name: {names.get(opcode, 'unknown')}", file=out)
            print(f"    sender_site_rva: \"{entry['sender_site_rva']:#010x}\"", file=out)
            print(f"    fields: [{', '.join(entry['fields'])}]", file=out)
            print(f"    via_helper: {str(entry['via_helper']).lower()}", file=out)
    print(f"{len(results)} senders recovered, {none} opcodes with no push-site sender -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
