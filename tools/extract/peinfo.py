#!/usr/bin/env python3
"""Read the identity of a PE image: hash, ImageBase, machine, link timestamp.

A binary fact is only true of a build (ADR 0003), and an observed absolute address only
converts to an RVA once the ImageBase is known. This produces the fields
`client/builds.yaml` needs, without copying the binary anywhere.

  python3 tools/extract/peinfo.py <file.dll|file.exe> [...]
  python3 tools/extract/peinfo.py --compare <stock> <patched>

`--compare` prints the section table of both images and, for every section they share,
whether its raw bytes are identical -- then lists each contiguous run of differing bytes
as an RVA and a loaded VA. That is what says whether addresses read from one build are
usable on the other.
"""

import datetime
import hashlib
import os
import struct
import sys

MACHINES = {0x014c: "i386", 0x8664: "x86-64", 0x01c0: "arm", 0xaa64: "arm64"}


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pe_identity(path):
    with open(path, "rb") as handle:
        data = handle.read(0x400)
    if data[:2] != b"MZ":
        raise ValueError("not a DOS/PE image")
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe:pe + 4] != b"PE\0\0":
        raise ValueError("PE signature not found")

    machine, sections, timestamp = struct.unpack_from("<HHI", data, pe + 4)
    optional = pe + 24
    magic = struct.unpack_from("<H", data, optional)[0]
    if magic == 0x10b:        # PE32
        image_base = struct.unpack_from("<I", data, optional + 28)[0]
        fmt = "PE32"
    elif magic == 0x20b:      # PE32+
        image_base = struct.unpack_from("<Q", data, optional + 24)[0]
        fmt = "PE32+"
    else:
        raise ValueError(f"unknown optional header magic {magic:#x}")
    size_of_image = struct.unpack_from("<I", data, optional + 56)[0]

    return {
        "format": fmt,
        "machine": MACHINES.get(machine, f"{machine:#06x}"),
        "image_base": image_base,
        "size_of_image": size_of_image,
        "sections": sections,
        "link_timestamp": datetime.datetime.fromtimestamp(
            timestamp, datetime.timezone.utc).isoformat(),
    }


def sections(path):
    """(name, rva, virtual_size, raw_offset, raw_size) for each section, in file order."""
    data = open(path, "rb").read()
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    count = struct.unpack_from("<H", data, pe + 6)[0]
    optional_size = struct.unpack_from("<H", data, pe + 20)[0]
    table = pe + 24 + optional_size
    out = []
    for index in range(count):
        entry = table + index * 40
        name = data[entry:entry + 8].rstrip(b"\0").decode("ascii", "replace")
        vsize, rva, rsize, raw = struct.unpack_from("<IIII", data, entry + 8)
        out.append((name, rva, vsize, raw, rsize))
    return data, out


def compare(stock_path, patched_path):
    base = pe_identity(stock_path)["image_base"]
    stock_data, stock = sections(stock_path)
    patched_data, patched = sections(patched_path)

    for label, path, table in (("stock", stock_path, stock),
                               ("patched", patched_path, patched)):
        print(f"{label}: {os.path.basename(path)}")
        for name, rva, vsize, raw, rsize in table:
            print(f"  {name:9} rva={rva:#010x} vsize={vsize:#010x} raw={raw:#010x}/{rsize:#010x}")

    by_name = {entry[0]: entry for entry in patched}
    print("\nshared sections:")
    for name, rva, vsize, raw, rsize in stock:
        if name not in by_name:
            print(f"  {name:9} absent from patched")
            continue
        other = by_name[name]
        same_rva = rva == other[1]
        equal = stock_data[raw:raw + rsize] == patched_data[other[3]:other[3] + other[4]]
        print(f"  {name:9} same_rva={same_rva} raw_equal={equal}")
        if equal or not same_rva:
            continue
        a = stock_data[raw:raw + rsize]
        b = patched_data[other[3]:other[3] + other[4]]
        runs = []
        for offset in range(min(len(a), len(b))):
            if a[offset] == b[offset]:
                continue
            if runs and offset == runs[-1][1] + 1:
                runs[-1][1] = offset
            else:
                runs.append([offset, offset])
        total = sum(end - start + 1 for start, end in runs)
        print(f"    {total} differing bytes in {len(runs)} run(s):")
        for start, end in runs:
            print(f"      rva={rva + start:#010x} va={base + rva + start:#010x}"
                  f"  stock={a[start:end + 1].hex()} patched={b[start:end + 1].hex()}")
    print("\nsections only in patched:",
          [entry[0] for entry in patched if entry[0] not in {e[0] for e in stock}])
    return 0


def main(argv):
    if argv[:1] == ["--compare"]:
        if len(argv) != 3:
            sys.exit("--compare takes exactly two images: <stock> <patched>")
        return compare(argv[1], argv[2])
    if not argv:
        sys.exit(__doc__)
    for path in argv:
        print(f"{path}")
        print(f"  sha256: {sha256(path)}")
        try:
            for key, value in pe_identity(path).items():
                print(f"  {key}: {value:#x}" if key in ("image_base", "size_of_image")
                      else f"  {key}: {value}")
        except ValueError as error:
            print(f"  error: {error}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
