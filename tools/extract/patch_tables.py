#!/usr/bin/env python3
"""Which client DBC table each SMSG_PATCH_* packet writes a row into.

Extensions.dll keeps its own copies of Ascension's custom DBC tables (CustomDBCMgr.cpp,
per the path string it logs). Its manager loads each with the idiom

    call <name getter>          ; `mov eax, "DBFilesClient\\X.dbc"; ret`
    ...
    mov ecx, <table instance>   ; a static object in .data
    call <loader>

and a SMSG_PATCH_* handler copies one row out of the packet into that instance (`rows`
at +0x20, `minId` at +0x10, `maxId` at +0xc of it). Pairing the two gives, per opcode,
the table whose row the packet carries; the dataset manifest gives that table's record
size and field count, which the handler's block copy should equal.

  python3 tools/extract/patch_tables.py <Extensions.dll> <c dir> --build <id> --manifest <dataset manifest> --out <file>
"""

import argparse
import hashlib
import importlib.util
import os
import re
import struct
import subprocess
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE_SPAN = 0x24        # the table objects sit 0x24 bytes apart in .data


def load_image(path):
    spec = importlib.util.spec_from_file_location("opcode_names", os.path.join(HERE, "opcode_names.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Image(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("dll")
    parser.add_argument("cdir")
    parser.add_argument("--build", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    image = load_image(args.dll)
    data = image.data

    # 1. every tiny name getter: `b8 <imm32> c3` whose immediate is a DBFilesClient string
    getters = {}
    text = next(s for s in image.sections if s[0] == ".text")
    raw, size, rva = text[3], text[4], text[1]
    for off in range(raw, raw + size - 6):
        if data[off] == 0xB8 and data[off + 5] == 0xC3:
            target = struct.unpack_from("<I", data, off + 1)[0]
            try:
                name = image.string(target)
            except Exception:
                continue
            if name and name.startswith("DBFilesClient"):
                getters[0x10000000 + rva + (off - raw)] = name.split("\\")[-1].split("/")[-1]

    # 2. the manager's idiom: call getter ... mov ecx, instance ... call loader
    listing = subprocess.run(["objdump", "-d", "-M", "intel", "--section=.text", args.dll],
                             capture_output=True, text=True).stdout
    lines = [l for l in listing.splitlines() if re.match(r"^\s*[0-9a-f]+:", l)]
    instances = {}
    for i, line in enumerate(lines):
        m = re.search(r"call\s+0x(10[0-9a-f]{6})$", line)
        if not m or int(m.group(1), 16) not in getters:
            continue
        name = getters[int(m.group(1), 16)]
        for follow in lines[i + 1:i + 16]:
            mm = re.search(r"mov\s+ecx,0x(10b[0-9a-f]{5})$", follow)
            if mm:
                instances[int(mm.group(1), 16)] = name
                break

    # 3. the handlers: any .data global inside an instance's span names the table -- in the
    # handler's own body, or in a function it calls (the insert helper of most tables),
    # read off the listing from the callee's entry to its first `ret` followed by padding.
    index = {}
    for k, line in enumerate(lines):
        m = re.match(r"^\s*([0-9a-f]+):", line)
        if m:
            index.setdefault(int(m.group(1), 16), k)
    memo = {}

    def callee_globals(entry):
        if entry in memo:
            return memo[entry]
        found = set()
        memo[entry] = found
        start = index.get(entry)
        if start is None:
            return found
        for line in lines[start:start + 400]:
            for g in re.findall(r"0x(10b[d-e][0-9a-f]{4})\b", line):
                found.add(int(g, 16))
            if re.search(r"\bret\b", line):
                break
        return found

    with open(args.manifest, encoding="utf-8") as handle:
        manifest = {t["name"]: t for t in yaml.safe_load(handle)["tables"]}
    spans = sorted(instances)
    results = {}
    for filename in sorted(os.listdir(args.cdir)):
        if not filename.endswith(".c"):
            continue
        opcode = int(filename[:-2], 16)
        with open(os.path.join(args.cdir, filename), encoding="utf-8", errors="replace") as handle:
            c = handle.read()
        globals_used = {int(g, 16) for g in re.findall(r"DAT_(10b[0-9a-f]{5})", c)}
        via = {}
        for callee in set(re.findall(r"FUN_(1[0-9a-f]{7})\(", c)):
            for g in callee_globals(int(callee, 16)):
                via.setdefault(g, f"FUN_{callee}")
        hit = {}
        direct = {}
        for g in globals_used:
            for base in spans:
                if base <= g < base + INSTANCE_SPAN:
                    direct[instances[base]] = base
        if direct:
            hit = direct
        else:
            # a callee binds only when it names exactly one table: a per-table insert helper,
            # not a shared routine that walks several
            per_callee = {}
            for g, callee in via.items():
                for base in spans:
                    if base <= g < base + INSTANCE_SPAN:
                        per_callee.setdefault(callee, set()).add(base)
            for callee, bases in per_callee.items():
                if len(bases) == 1:
                    base = next(iter(bases))
                    hit[instances[base]] = base
        if not hit:
            continue
        block = re.search(r"\+ 0x14\) = (\w+) \+ (0x[0-9a-f]+);", c)
        results[opcode] = {"tables": {name: f"{base:#010x}" for name, base in sorted(hit.items())},
                           "manifest": {name: {"record_size": manifest[name]["record_size"], "fields": manifest[name]["fields"]}
                                        for name in hit if name in manifest}}

    with open(args.out, "w", encoding="utf-8") as out:
        print("# Generated by tools/extract/patch_tables.py -- do not hand-edit.", file=out)
        print(f"build: {args.build}", file=out)
        print(f"sha256: {hashlib.sha256(data).hexdigest()}", file=out)
        print(f"dataset: {os.path.basename(args.manifest).split('.manifest')[0]}", file=out)
        print("# The DLL's custom DBC tables: name getter -> table instance in .data (CustomDBCMgr's load", file=out)
        print("# idiom), then per opcode the instance(s) its handler touches and the table's record size", file=out)
        print("# and field count from the dataset manifest.", file=out)
        print(f"name_getters: {len(getters)}", file=out)
        print(f"instances: {len(instances)}", file=out)
        print("tables:", file=out)
        for base in spans:
            print(f"  {instances[base]}: {{instance: \"{base:#010x}\"}}", file=out)
        print(f"opcodes: {len(results)}", file=out)
        print("handlers:", file=out)
        for opcode in sorted(results):
            entry = results[opcode]
            print(f"  {opcode:#06x}:", file=out)
            for name, base in entry["tables"].items():
                info = entry["manifest"].get(name)
                extra = f", record_size: {info['record_size']}, fields: {info['fields']}" if info else ", record_size: null, fields: null"
                print(f"    - {{dbc: {name}, instance: \"{base}\"{extra}}}", file=out)
    print(f"{len(getters)} name getters, {len(instances)} table instances, {len(results)} handlers bound -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
