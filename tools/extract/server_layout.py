#!/usr/bin/env python3
"""What the CoA server WRITES into each packet, and whether it matches what the client READS.

For every `WorldPacket <var>(<opcode>, ...)` in the server module, collect the `<var> <<`
chain that follows and classify each operand by width -- `uint8(x)` is a u8, `float(x)`
an f32, a quoted or std::string operand a cstring. A bare variable has no visible width
and is recorded as `?`. Trailing `// comments` are kept as the best available field names.

Then diff against the client's recovered read sequence. A match means the server's names
can be lent to the client's widths; a mismatch is a live bug, or an extractor limit, and
either way is worth a human's eyes before anything ships.

  python3 tools/extract/server_layout.py <azerothcore checkout> --build <id> --out <file>
"""

import argparse
import os
import re
import sys

import yaml

PACKET = re.compile(r"WorldPacket\s+(?P<var>\w+)\s*\(\s*(?P<opcode>[A-Za-z][A-Za-z0-9_]*|0x[0-9A-Fa-f]+)")
CONST = re.compile(r"constexpr\s+uint16\s+(?P<name>[A-Z0-9_]+)\s*=\s*0x(?P<hex>[0-9A-Fa-f]+)")
# Manastorm defines its opcodes as `enum Opcode : std::uint16_t { Enter = 0x651, ... }`
# with short member names. Any `Name = 0xNNN` inside an enum body counts.
ENUM_MEMBER = re.compile(r"\b(?P<name>[A-Z][A-Za-z0-9_]*)\s*=\s*0x(?P<hex>[0-9A-Fa-f]{3,4})\b")
# `uint8(x)`, `static_cast<uint8>(x)` and `fields[n].Get<uint8>()` all fix the width;
# a bare variable does not, and stays `?`.
WIDTH_OF = [
    (re.compile(r"(^|<)u?int8\s*[>(]"), "u8"), (re.compile(r"(^|<)u?int16\s*[>(]"), "u16"),
    (re.compile(r"(^|<)u?int32\s*[>(]"), "u32"), (re.compile(r"(^|<)u?int64\s*[>(]"), "u64"),
    (re.compile(r"(^|<)float\s*[>(]"), "f32"), (re.compile(r"(^|<)double\s*[>(]"), "f64"),
    (re.compile(r"^(std::string|\")|Get<std::string>"), "cstring"),
    (re.compile(r"GUID|ObjectGuid"), "u64"),
]


def classify(operand):
    operand = operand.strip()
    for pattern, kind in WIDTH_OF:
        if pattern.match(operand):
            return kind
    return "unknown"      # a bare variable: no visible width (never `?`, which YAML reads as a key marker)


SIZE = {"u8": 1, "u16": 2, "u32": 4, "u64": 8, "f32": 4, "f64": 8}


def by_offsets(server_seq, client_seq):
    """Compare by byte boundaries: the client often block-copies a record the server writes
    field by field (`bytes_26` against six writes), and a loop shows up flat on one side.
    The two agree when every boundary the client stops at is a boundary the server has,
    over the prefix both sides describe with known widths."""
    def boundaries(seq):
        out, pos = [], 0
        for kind in seq:
            if kind == "unknown" or kind == "lpstring":
                return out, pos, True         # unknown width: the prefix ends here
            width = SIZE.get(kind)
            if width is None:
                m = re.match(r"bytes_(\d+)$", kind)
                if not m:
                    return out, pos, True
                width = int(m.group(1))
            pos += width
            out.append(pos)
        return out, pos, False
    # A client block copy of N bytes (`bytes_N`) is one record the server writes field by
    # field, usually inside a loop the flat chain shows once (and a branch may add a
    # count before it): agree when some contiguous run of server fields sums to N.
    for kind in client_seq:
        m = re.match(r"bytes_(\d+)$", kind)
        if not m:
            continue
        target, sizes = int(m.group(1)), [SIZE.get(k, 0) for k in server_seq]
        for start in range(len(sizes)):
            total = 0
            for end in range(start, len(sizes)):
                total += sizes[end]
                if total == target and all(sizes[start:end + 1]):
                    return f"agree-by-record ({target}-byte record = server fields {start}..{end})"
                if total > target:
                    break
    sb, slen, s_cut = boundaries(server_seq)
    cb, clen, c_cut = boundaries(client_seq)
    prefix = min(slen, clen)
    s_in = [b for b in sb if b <= prefix]
    c_in = [b for b in cb if b <= prefix]
    if not c_in or not s_in:
        return f"DISAGREE (server {len(server_seq)} fields, client {len(client_seq)})"
    if all(b in sb for b in c_in) or all(b in cb for b in s_in):
        if slen == clen and not s_cut and not c_cut:
            return "agree-by-size"
        return f"agree-by-size over the first {prefix} bytes"
    return f"DISAGREE (server {len(server_seq)} fields, client {len(client_seq)}; boundaries differ)"


def chains(text, var):
    """Every `<var> << a << b ...;` statement, as (operands, comments) in source order.

    Two idioms write the client's length-prefixed string (u32 length, bytes, no NUL --
    FUN_100d3680 on the client): `AppendConfigString(var, s)` and `var << uint32(s.size()
    + 1); var.append(s.c_str(), s.size() + 1)`. Both become one `lpstring`.
    """
    out = []
    pattern = re.compile(rf"\b{re.escape(var)}\s*<<(?P<body>.*?);|AppendConfigString\s*\(\s*{re.escape(var)}\s*,\s*(?P<lp>[^)]*)\)\s*;|"
                         rf"\b{re.escape(var)}\.append\s*\((?P<app>[^;]*)\)\s*;", re.S)
    for match in pattern.finditer(text):
        if match.group("lp") is not None:
            out.append(("lpstring", "", "AppendConfigString(" + match.group("lp").strip()[:40] + ")"))
            continue
        if match.group("app") is not None:
            if out and out[-1][0] == "u32" and "size()" in out[-1][2]:
                out[-1] = ("lpstring", out[-1][1], match.group("app").strip()[:60])
            else:
                out.append(("bytes", "", "append(" + match.group("app").strip()[:50] + ")"))
            continue
        body = match.group("body")
        for piece in re.split(r"<<", body):
            code, _, comment = piece.partition("//")
            code = code.strip()
            if not code:
                continue
            out.append((classify(code), comment.strip().split("\n")[0], code[:60]))
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("core")
    parser.add_argument("--module", action="append",
                        help="module directory under the core, repeatable (default: mod-ascension-compat and mod-coa-challenges)")
    parser.add_argument("--build", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    layouts_path = os.path.join(root, "client", "symbols", args.build, "layouts.yaml")
    with open(layouts_path, encoding="utf-8") as handle:
        client = yaml.safe_load(handle)["layouts"]
    client = {(int(k, 16) if isinstance(k, str) else int(k)): v["fields"]
              for k, v in client.items()}
    # The decompiled read sequence (handler-fire.yaml) sees the length-prefixed strings the
    # asm idiom cannot; where it exists it is the client side of the comparison.
    decompiled = set()
    fire_path = os.path.join(root, "client", "symbols", args.build, "handler-fire.yaml")
    if os.path.isfile(fire_path):
        with open(fire_path, encoding="utf-8") as handle:
            fire = yaml.safe_load(handle)["handlers"]
        widths = {1: "u8", 2: "u16", 4: "u32", 8: "u64", "lpstring": "lpstring", "cstring": "cstring", "var": "unknown"}
        for key, entry in fire.items():
            opcode = int(key, 16) if isinstance(key, str) else int(key)
            def flatten(entries):
                for read in entries:
                    if isinstance(read, dict) and "repeat" in read:
                        yield from flatten(read["reads"])
                    else:
                        yield read
            reads = list(flatten(entry.get("reads") or []))
            if reads:
                client[opcode] = [widths.get(r[1] if isinstance(r, list) else r["width"], f"bytes_{r[1] if isinstance(r, list) else r['width']}") for r in reads]
                decompiled.add(opcode)

    modules = args.module or ["modules/mod-ascension-compat", "modules/mod-coa-challenges"]
    constants, writes, unresolved, sources = {}, {}, [], {}
    # The core's own Opcodes.h names the fork's constants (SMSG_COA_*): resolve those too.
    opcodes_h = os.path.join(args.core, "src/server/game/Server/Protocol/Opcodes.h")
    if os.path.isfile(opcodes_h):
        with open(opcodes_h, encoding="utf-8", errors="replace") as handle:
            for match in re.finditer(r"^\s*((?:CMSG|SMSG|MSG)_[A-Z0-9_]+)\s*=\s*0x([0-9A-Fa-f]{1,4})\s*,", handle.read(), re.M):
                constants.setdefault(match.group(1), int(match.group(2), 16))
    for module_rel in modules:
        module = os.path.join(args.core, module_rel)
        for dirpath, _, files in os.walk(module):
            for filename in files:
                if not filename.endswith((".cpp", ".h")) or "Test" in filename:
                    continue
                path = os.path.join(dirpath, filename)
                with open(path, encoding="utf-8", errors="replace") as handle:
                    text = handle.read()
                sources[os.path.relpath(path, args.core)] = text
                for match in CONST.finditer(text):
                    constants[match.group("name")] = int(match.group("hex"), 16)
                for enum in re.finditer(r"enum\s+(?:class\s+)?\w+\s*(?::[^{]+)?\{(?P<body>[^}]*)\}", text):
                    for match in ENUM_MEMBER.finditer(enum.group("body")):
                        constants.setdefault(match.group("name"), int(match.group("hex"), 16))
    for relative, text in sources.items():
        for match in PACKET.finditer(text):
            token = match.group("opcode")
            # Only the chain that follows THIS construction, up to the next WorldPacket.
            tail = text[match.end():]
            nxt = PACKET.search(tail)
            scope = tail[:nxt.start()] if nxt else tail
            fields = chains(scope, match.group("var"))
            targets = []
            if token.startswith("0x"):
                targets = [int(token, 16)]
            elif token in constants:
                targets = [constants[token]]
            else:
                # The opcode is a parameter of a helper: every call site that passes a known
                # constant in that position attributes the chain to that opcode.
                head = text[:match.start()]
                sig = None
                for candidate in re.finditer(r"\b(\w+)\s*\(([^)]*)\)\s*(?:const\s*)?\{", head):
                    if re.search(rf"\b{re.escape(token)}\b", candidate.group(2)):
                        sig = candidate
                if sig:
                    params = [p.strip().split()[-1].lstrip("*&") for p in sig.group(2).split(",") if p.strip()]
                    position = params.index(token) if token in params else None
                    for other in sources.values():
                        for call in re.finditer(rf"\b{re.escape(sig.group(1))}\s*\(([^;]*?)\)\s*;", other):
                            call_args = [a.strip() for a in call.group(1).split(",")]
                            if position is not None and position < len(call_args) and call_args[position] in constants:
                                targets.append(constants[call_args[position]])
                    targets = sorted(set(targets))
                    # widths of bare parameters come from the signature
                    types = {p.strip().split()[-1].lstrip("*&"): " ".join(p.strip().split()[:-1]) for p in sig.group(2).split(",") if p.strip()}
                    fields = [(classify(types.get(code, "") + "(x)") if kind == "unknown" and code in types else kind, comment, code)
                              for kind, comment, code in fields]
                if not targets:
                    unresolved.append((relative, token))
                    continue
            for opcode in targets:
                if fields:
                    writes.setdefault(opcode, []).append({"file": relative, "fields": fields})

    with open(args.out, "w", encoding="utf-8") as out:
        print("# Generated by tools/extract/server_layout.py -- do not hand-edit.", file=out)
        print(f"modules: [{', '.join(modules)}]", file=out)
        print("# Per opcode: what the server writes (width, comment, code) and whether the", file=out)
        print("# client's recovered read sequence agrees. `unknown` is a bare variable of unknown width.", file=out)
        print("opcodes:", file=out)
        agree = disagree = unknown = 0
        for opcode in sorted(writes):
            print(f"  {opcode:#06x}:", file=out)
            for site in writes[opcode]:
                print(f"    - file: {site['file']}", file=out)
                print("      writes:", file=out)
                for kind, comment, code in site["fields"]:
                    tag = f"  # {comment}" if comment else ""
                    print(f"        - [{kind}, \"{code.replace(chr(34), chr(39))}\"]{tag}", file=out)
                widths = [k for k, _, _ in site["fields"]]
                reads = client.get(opcode)
                # The client extractor cannot see every string, so drop cstrings from both
                # sides before comparing: widths must agree position by position on what
                # remains, with a bare `?` matching anything.
                # The asm extractor cannot see every string, so against ITS reads the strings are
                # dropped on both sides; the decompiled reads type them, and are compared whole,
                # a server operand of unknown width matching a string as well as a number.
                if opcode in decompiled:
                    server_seq, client_seq = list(widths), list(reads or [])
                else:
                    server_seq, client_seq = [w for w in widths if w not in ("cstring", "lpstring")], [r for r in (reads or []) if r != "cstring"]
                if reads is None:
                    verdict = "no-client-layout"
                else:
                    same = lambda w, r: (w == "unknown" or r == "unknown" or w == r or (w == "f32" and r == "u32")
                                         or (w in ("cstring", "lpstring", "bytes") and r in ("cstring", "lpstring")))
                    if len(server_seq) == len(client_seq) and all(same(w, r) for w, r in zip(server_seq, client_seq)):
                        verdict = "agree" if "unknown" not in server_seq and "unknown" not in client_seq else "agree-where-visible"
                    else:
                        verdict = by_offsets(server_seq, client_seq)
                print(f"      client_reads: [{', '.join(reads)}]" if reads else
                      "      client_reads: null", file=out)
                print(f"      verdict: {verdict}", file=out)
                agree += verdict.startswith("agree")
                disagree += verdict.startswith("DISAGREE")
                unknown += verdict == "no-client-layout"
        print("# WorldPacket constructions whose opcode is a variable or expression and could", file=out)
        print("# not be attributed statically. They are NOT covered by the verdicts above.", file=out)
        print("unresolved:", file=out)
        for relative, token in unresolved:
            print(f"  - {{file: {relative}, opcode_expr: \"{token}\"}}", file=out)
    print(f"{len(writes)} opcodes written by the server: {agree} agree with the client,"
          f" {disagree} DISAGREE, {unknown} have no client layout;"
          f" {len(unresolved)} constructions unresolved -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
