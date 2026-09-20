#!/usr/bin/env python3
"""Infer a packet's wire layout from the code that reads it.

The client reads a packet through a cursor. Every field comes out as the same shape: load
from `[base + cursor]`, advance the cursor by the field's width, store it back into the
packet object at `+0x14`.

    mov eax,DWORD PTR [esi+ecx*1]    ; read u32
    add ecx,0x4                      ; advance
    mov DWORD PTR [edx+0x14],ecx     ; store the cursor

    mov al,BYTE PTR [esi+ecx*1]      ; read u8
    inc ecx

So walking a handler's disassembly in address order and recording each (load, advance)
pair recovers the field sequence. Two forms of advance appear: an explicit `add`/`inc`,
and a folded `lea <r>,[<cursor>+N]` that covers several loads at once.

This only sees what a function reads **itself**. A handler that delegates to a
deserializer is followed one level down, into the first callee that touches a cursor.

What comes out is a field sequence with widths -- not field names and not meanings. It is
`L3`: read from the instructions, no more.

  python3 tools/extract/packet_layout.py <Extensions.dll> --build <id> --out <file>
"""

import argparse
import collections
import os
import re
import struct
import subprocess
import sys
import importlib.util

import yaml

LOAD = re.compile(
    r"(?P<op>mov|movss|movsd)\s+(?P<dst>[a-z0-9]+),(?P<size>BYTE|WORD|DWORD|QWORD) PTR "
    r"\[(?P<b>e[a-z]{2})\+(?P<c>e[a-z]{2})\*1(?:\+0x(?P<disp>[0-9a-f]+))?\]")
ADD = re.compile(r"add\s+(?P<reg>e[a-z]{2}),0x(?P<imm>[0-9a-f]+)$")
INC = re.compile(r"inc\s+(?P<reg>e[a-z]{2})$")
LEA = re.compile(r"lea\s+(?P<dst>e[a-z]{2}),\[(?P<src>e[a-z]{2})\+0x(?P<imm>[0-9a-f]+)\]")
CURSOR_STORE = re.compile(r"mov\s+DWORD PTR \[(?P<pkt>e[a-z]{2})\+0x14\],(?P<reg>e[a-z]{2})")
# Tried and dropped: requiring the store to target the register the cursor was first
# loaded from. The deserializers reload the packet pointer into other registers, so that
# rule lost real fields (0x0726's last two) without removing the phantoms it was meant to.
CALL = re.compile(r"call\s+0x(?P<target>[0-9a-f]+)")
# A string is not advanced by a fixed width: the client takes a pointer into the buffer at
# the cursor and scans for the terminator. `lea <r>,[base+cursor*1]` with no displacement,
# on a register already established as a cursor, is that.
STRING_AT_CURSOR = re.compile(r"lea\s+e[a-z]{2},\[(?P<b>e[a-z]{2})\+(?P<c>e[a-z]{2})\*1\]$")
# NOT modelled: strings read through the std::string helpers (0x10086dd0 allocates,
# 0x10086e30 assigns). Counting those calls as packet strings was tried and produced false
# positives -- any std::string built inside a handler looked like a field, and 0x0725 grew
# a string it does not read. A std::string's length also sits at +0x14, the same offset as
# the packet cursor, so that store is not a safe signal either.
WIDTH = {"BYTE": 1, "WORD": 2, "DWORD": 4, "QWORD": 8}
LOOKAHEAD = 6   # instructions within which the advanced cursor must be stored back
# A float is read with movss and is the same width as a u32; the opcode is what
# separates them, so the width carries a kind alongside it.
TYPE = {(1, False): "u8", (2, False): "u16", (4, False): "u32", (8, False): "u64",
        (4, True): "f32", (8, True): "f64", (0, False): "cstring"}


def load_image(path):
    spec = importlib.util.spec_from_file_location(
        "opcode_names", os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "opcode_names.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Image(path)


def disassemble(image, rva, length, scratch):
    offset = image.offset(image.base + rva)
    if offset is None:
        return []
    with open(scratch, "wb") as handle:
        handle.write(image.data[offset:offset + length])
    result = subprocess.run(
        ["objdump", "-D", "-b", "binary", "-m", "i386", "-M", "intel",
         f"--adjust-vma={image.base + rva:#x}", scratch],
        capture_output=True, text=True)
    out = []
    for line in result.stdout.splitlines():
        if ":\t" not in line:
            continue
        address, _, rest = line.partition(":\t")
        parts = rest.split("\t", 1)
        if len(parts) != 2:
            continue
        out.append((int(address.strip(), 16), parts[1].strip()))
    return out


def function_end(listing):
    """Stop at the first int3 run, which MSVC pads functions with."""
    padding = 0
    for index, (_, text) in enumerate(listing):
        if text == "int3":
            padding += 1
            if padding >= 2:
                return index - 1
        else:
            padding = 0
    return len(listing)


def read_fields(listing):
    """Field widths in the order the code reads them.

    A load is `[base + cursor*1]`, and which of the two registers is the cursor is not
    visible at the instruction: both orders occur. So a pending load is remembered under
    **both** registers, and whichever one the next advance names decides it.

    A packet read is only counted once the advanced cursor is **stored back into the
    packet object** -- `mov DWORD PTR [pkt+0x14], <cursor>` within a few instructions.
    Without that rule, ordinary pointer arithmetic after the real reads (a map insert, a
    std::string being built) matched the same load/advance shape and grew phantom fields:
    0x0771 read as nine fields when the client takes six, 0x0769 grew a u32 it never reads.
    """
    fields, pending, waiting = [], [], []   # pending loads; advances not yet satisfiable
    cursors = set()                          # registers proven to be cursors
    provisional = []                         # (fields, register, remaining lookahead)

    def consume(register, step, stored_as):
        taken, total, index = [], 0, 0
        while index < len(pending) and total < step:
            regs, width, is_float = pending[index]
            if register not in regs or total + width > step:
                break
            taken.append((width, is_float))
            total += width
            index += 1
        if taken and total == step:
            del pending[:index]
            cursors.add(register)
            provisional.append([taken, stored_as, LOOKAHEAD])
            return True
        return False

    def settle():
        index = 0
        while index < len(waiting):
            register, step, stored_as = waiting[index]
            if consume(register, step, stored_as):
                del waiting[index]
                index = 0
            else:
                index += 1

    def advance(register, step, stored_as):
        if not consume(register, step, stored_as):
            waiting.append((register, step, stored_as))

    def tick(text):
        """Confirm provisional fields when their cursor is stored; expire the rest."""
        store = CURSOR_STORE.search(text)
        for entry in list(provisional):
            taken, stored_as, remaining = entry
            if store and store.group("reg") == stored_as:
                fields.extend(taken)
                provisional.remove(entry)
                continue
            entry[2] = remaining - 1
            if entry[2] <= 0:
                provisional.remove(entry)

    for _, text in listing:
        tick(text)
        load = LOAD.search(text)
        if load:
            pending.append(({load.group("b"), load.group("c")},
                            WIDTH[load.group("size")],
                            load.group("op") in ("movss", "movsd")))
            settle()
            continue
        add = ADD.search(text)
        if add:
            advance(add.group("reg"), int(add.group("imm"), 16), add.group("reg"))
            continue
        inc = INC.search(text)
        if inc:
            advance(inc.group("reg"), 1, inc.group("reg"))
            continue
        lea = LEA.search(text)
        if lea:
            advance(lea.group("src"), int(lea.group("imm"), 16), lea.group("dst"))
            continue
        at_cursor = STRING_AT_CURSOR.search(text)
        if at_cursor and not pending and (
                at_cursor.group("b") in cursors or at_cursor.group("c") in cursors):
            fields.append((0, False))        # cstring: length only known at runtime
    return fields


def reads_a_cursor(listing):
    return any(CURSOR_STORE.search(text) for _, text in listing)


def analyse(image, rva, scratch, depth=1):
    listing = disassemble(image, rva, 0x900, scratch)
    listing = listing[:function_end(listing)]
    if not listing:
        return [], None
    fields = read_fields(listing) if reads_a_cursor(listing) else []
    if fields or depth == 0:
        return fields, rva
    # The handler delegated: follow the first callee that reads a cursor itself.
    for _, text in listing:
        call = CALL.search(text)
        if not call:
            continue
        target = int(call.group("target"), 16) - image.base
        if not 0 < target < 0x1000000:
            continue
        inner, source = analyse(image, target, scratch, depth - 1)
        if inner:
            return inner, source
    return [], None


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("dll")
    parser.add_argument("--build", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--only", type=lambda v: int(v, 0), action="append")
    args = parser.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    symbols = os.path.join(root, "client", "symbols", args.build)
    with open(os.path.join(symbols, "handlers.yaml"), encoding="utf-8") as handle:
        handlers = yaml.safe_load(handle)["handlers"]
    handlers = {(int(k, 16) if isinstance(k, str) else int(k)): v
                for k, v in handlers.items()}

    image = load_image(args.dll)
    scratch = os.path.join(os.path.dirname(args.out), ".layout-scratch.bin")
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)

    results, empty = {}, 0
    for opcode, entry in sorted(handlers.items()):
        if args.only and opcode not in args.only:
            continue
        rva = entry["sites"][0]["handler_rva"]
        fields, source = analyse(image, rva, scratch)
        if not fields:
            empty += 1
            continue
        results[opcode] = {"read_in_rva": source, "fields": fields}

    if os.path.exists(scratch):
        os.remove(scratch)

    with open(args.out, "w", encoding="utf-8") as out:
        print("# Generated by tools/extract/packet_layout.py -- do not hand-edit.", file=out)
        print(f"build: {args.build}", file=out)
        print("# Field WIDTHS in read order. Not names, not meanings. A handler that", file=out)
        print("# reads nothing inline and delegates more than one level deep is absent.", file=out)
        print(f"recovered: {len(results)}", file=out)
        print(f"no_inline_reads: {empty}", file=out)
        print("layouts:", file=out)
        for opcode in sorted(results):
            entry = results[opcode]
            types = [TYPE[key] for key in entry["fields"]]
            print(f"  {opcode:#06x}:", file=out)
            print(f"    read_in_rva: \"{entry['read_in_rva']:#010x}\"", file=out)
            print(f"    fields: [{', '.join(types)}]", file=out)

    print(f"{len(results)} layouts recovered, {empty} handlers with no inline reads"
          f" -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
