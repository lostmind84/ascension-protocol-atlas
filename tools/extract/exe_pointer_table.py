#!/usr/bin/env python3
"""The table of Ascension.exe addresses Extensions.dll calls through, with what each does.

Extensions.dll keeps, in its .data at 0x10bc90a0.., a static table of function pointers
into Ascension.exe (`call [0x10bc90cc]` in every sender). This lists every slot whose value
lies in the exe's image, how many call sites in the DLL use it, and -- for the slots read
by hand from the exe's decompilation -- what the function does. Roles are hand-curated in
ROLES below and cite the reading in client/wire-path.md; every other slot is `unlabelled`.

  python3 tools/extract/exe_pointer_table.py <Extensions.dll> --build <id> --out <file>
"""

import argparse
import hashlib
import importlib.util
import os
import re
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EXE_BASE, EXE_SIZE = 0x400000, 0x9fc000
TABLE_START, TABLE_END = 0x10bc9000, 0x10bcc000

# slot -> (exe VA, role), from the decompiled exe functions (client/wire-path.md)
ROLES = {
    0x10bc90bc: "CDataStore::CDataStore -- constructor: vtable 0x9e0e24, buffer/base/capacity/size zeroed, read pos -1",
    0x10bc90c0: "CDataStore::Put(u8)",
    0x10bc90c4: "CDataStore::Put(u16)",
    0x10bc90c8: "CDataStore::Put -- three-argument variant (u32, u16), not read further",
    0x10bc90d0: "CDataStore::Put(u64) -- 8 bytes",
    0x10bc90d4: "CDataStore::Put(float) -- 4 bytes, distinct from Put(u32)",
    0x10bc90e8: "CDataStore::Get(u32)",
    0x10bc90ec: "CDataStore::Get(u64)",
    0x10bc90f0: "CDataStore::Get(float) -- 4 bytes",
    0x10bc90f4: "CDataStore::GetString(buf, max) -- copies up to the NUL, advances past it",
    0x10bc90f8: "CDataStore::GetData(ptr, size)",
    0x10bc90cc: "CDataStore::Put(u32) -- the opcode is written with it first, then any u32 field",
    0x10bc90dc: "CDataStore::PutData(ptr, size)",
    0x10bc90d8: "CDataStore::PutString(cstr) -- strlen+1 bytes: NUL-terminated",
    0x10bc90fc: "CDataStore::Finalize -- resets the read position (+0x14) to 0; NOT the send",
    0x10bc9100: "CDataStore::~CDataStore -- frees the buffer",
    0x10bc9104: "CDataStore::Get(u8)",
    0x10bc90e0: "CDataStore::Get(u8) (same target as 0x10bc9104)",
    0x10bc90e4: "CDataStore::Get(u16)",
    0x10bc91e8: "ClientServices::Send wrapper (0x406f40): ensures the singleton, then 0x632b50",
    0x10bc91ec: "ClientServices::Send (0x632b50): state 5 = connected; encrypts the header when +0x538 is set; queues the bytes",
    0x10bc91f0: "ClientServices instance check (0x6b0970)",
    0x10bc93b8: "FrameScript_SignalEvent -- fires a UI event with a printf-like format and arguments",
    # Lua 5.1 C API, labelled by behaviour on the 16-byte TValue (tag at +8: 0 nil, 1 boolean,
    # 3 number, 4 string, 5 table, 6 function); GHIDRA_PROGRAM=Ascension.exe.ORIGINAL Decomp.java
    0x10bc90a0: "lua_setfield(L, idx, k) -- pushes the key string, then settable",
    0x10bc90a4: "lua_pushcclosure(L, fn, n) -- TValue tag 6",
    0x10bc90a8: "lua_createtable(L, narr, nrec) -- TValue tag 5",
    0x10bc90ac: "lua_pushinteger(L, n) -- an int widened to a double, tag 3",
    0x10bc90b0: "lua_pushboolean(L, b) -- tag 1",
    0x10bc90b4: "lua_settable(L, idx)",
    0x10bc90b8: "lua_checkstack(L, n) -- refuses past 0x800 slots",
    0x10bc92e8: "lua_pushnil(L) -- tag 0",
    0x10bc92e4: "lua_pushnumber(L, double) -- tag 3",
    0x10bc92dc: "lua_toboolean(L, idx)",
    0x10bc92e0: "lua_tolstring(L, idx, &len) -- converts a number in place first",
    0x10bc92c0: "lua_pushstring(L, s) -- nil when s is NULL",
    0x10bc93c4: "lua_type(L, idx) -- -1 for none",
    0x10bc93c8: "lua_gettop(L)",
    0x10bc93bc: "lua_settop(L, idx)",
    0x10bc93c0: "lua_isstring(L, idx) -- tag 4 or 3",
    0x10bc93cc: "lua_isnumber(L, idx) -- tag 3 or convertible",
    0x10bc9768: "lua_getfield(L, idx, k)",
    0x10bc92d8: "returns DAT_00d3f78c (a client global; not read further)",
    0x10bc92cc: "unit token for an ObjectGuid -- writes player/vehicle/target/party%d/partypet%d into the token buffers",
}


def load_image(path):
    spec = importlib.util.spec_from_file_location("opcode_names", os.path.join(HERE, "opcode_names.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Image(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("dll")
    parser.add_argument("--build", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    image = load_image(args.dll)

    listing = subprocess.run(["objdump", "-d", "-M", "intel", "--section=.text", args.dll],
                             capture_output=True, text=True).stdout
    uses = {}
    for match in re.finditer(r"ds:(0x10bc9[0-9a-f]{3})", listing):
        uses[int(match.group(1), 16)] = uses.get(int(match.group(1), 16), 0) + 1

    slots = []
    for va in range(TABLE_START, TABLE_END, 4):
        try:
            value = struct.unpack_from("<I", image.data, image.offset(va))[0]
        except Exception:
            break
        if EXE_BASE <= value < EXE_BASE + EXE_SIZE:
            slots.append((va, value, uses.get(va, 0)))

    with open(args.out, "w", encoding="utf-8") as out:
        print("# Generated by tools/extract/exe_pointer_table.py -- do not hand-edit (roles: ROLES in the script).", file=out)
        print(f"build: {args.build}", file=out)
        print(f"sha256: {hashlib.sha256(image.data).hexdigest()}", file=out)
        print("exe_build: ascension-exe-2010-06-25-stock", file=out)
        print("# slot: the DLL's pointer cell; exe_va: the Ascension.exe function it holds; uses: call sites in", file=out)
        print("# the DLL's .text; role: read from the exe's decompilation (client/wire-path.md) or unlabelled.", file=out)
        print(f"slots: {len(slots)}", file=out)
        print(f"labelled: {sum(1 for va, _, _ in slots if va in ROLES)}", file=out)
        print("table:", file=out)
        for va, value, count in slots:
            role = ROLES.get(va, "unlabelled")
            print(f"  {va:#x}: {{exe_va: \"{value:#010x}\", uses: {count}, role: \"{role}\"}}", file=out)
    print(f"{len(slots)} exe pointers, {sum(1 for va, _, _ in slots if va in ROLES)} labelled -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
