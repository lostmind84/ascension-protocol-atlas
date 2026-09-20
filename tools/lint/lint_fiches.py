#!/usr/bin/env python3
"""Validate the protocol fiches.

This linter is the fiche schema (ADR 0002). It checks shape, but mostly it checks the
rules that make the evidence ladder mean something: a fiche is only as strong as its
weakest field, and a claim of proof has to point at something executable.

Usage:  python3 tools/lint/lint_fiches.py [--root <repo root>]
Exit code 0 when every fiche is valid.
"""

import argparse
import os
import re
import sys

try:
    import yaml
except ImportError:
    sys.exit("pyyaml is required: python3 -m pip install --user pyyaml")

LEVELS = ["L0", "L1", "L2", "L3", "L4", "L5"]
STATUSES = ["unknown", "hypothetical", "proven", "deprecated"]
DIRECTIONS = {"server_to_client": "smsg", "client_to_server": "cmsg"}
REQUIRED = ["id", "name", "direction", "status", "evidence", "client_builds",
            "summary", "layout", "provenance"]
FILENAME_RE = re.compile(r"^0x([0-9a-f]{4})-(smsg|cmsg)-[a-z0-9-]+\.yaml$")


class Report:
    def __init__(self):
        self.errors = []

    def fail(self, where, message):
        self.errors.append(f"{where}: {message}")


def rank(level):
    return LEVELS.index(level) if level in LEVELS else -1


def layout_items(entries, prefix):
    """Walk a layout, descending into `repeat` blocks however deeply they nest."""
    for index, entry in enumerate(entries or []):
        if "repeat" in entry:
            yield from layout_items(entry.get("fields"), f"{prefix}[{index}].fields")
        else:
            yield f"{prefix}[{index}].{entry.get('name', '?')}", entry.get("evidence")


def graded_items(fiche):
    """Every (path, level) pair the fiche grades, layout and client symbols alike."""
    yield from layout_items(fiche.get("layout"), "layout")
    client = fiche.get("client") or {}
    if isinstance(client.get("deserializer"), dict):
        yield "client.deserializer", client["deserializer"].get("evidence")
    for index, consumer in enumerate(client.get("consumers") or []):
        yield f"client.consumers[{index}]", consumer.get("evidence")
    if isinstance(client.get("struct"), dict):
        yield "client.struct", client["struct"].get("evidence")


def client_symbols(fiche):
    client = fiche.get("client") or {}
    if isinstance(client.get("deserializer"), dict):
        yield "client.deserializer", client["deserializer"]
    for index, consumer in enumerate(client.get("consumers") or []):
        yield f"client.consumers[{index}]", consumer


def load_ids(path, key, report, where):
    """Read the `id` of every entry under `key` in a registry file."""
    ids = set()
    if not os.path.isfile(path):
        report.fail(where, "missing")
        return ids
    with open(path, encoding="utf-8") as handle:
        registry = yaml.safe_load(handle) or {}
    for entry in registry.get(key) or []:
        if isinstance(entry, dict) and entry.get("id"):
            ids.add(entry["id"])
    if not ids:
        report.fail(where, f"declares no {key}")
    return ids


def load_baseline(path, report):
    """Opcodes AzerothCore already defines. The atlas documents the complement (ADR 0005)."""
    if not os.path.isfile(path):
        report.fail("protocol/known-baseline.yaml",
                    "missing -- regenerate with tools/extract/ac_baseline.py")
        return {}
    with open(path, encoding="utf-8") as handle:
        baseline = yaml.safe_load(handle) or {}
    return {(int(k, 16) if isinstance(k, str) else int(k)): v for k, v in (baseline.get("opcodes") or {}).items()}


def check_fiche(path, fiche, known_builds, known_datasets, baseline, root, report):
    where = os.path.relpath(path, root)

    if not isinstance(fiche, dict):
        report.fail(where, "fiche is not a mapping")
        return

    for key in REQUIRED:
        if key not in fiche:
            report.fail(where, f"missing required key '{key}'")
    if any(key not in fiche for key in REQUIRED):
        return

    # Filename must state the opcode and direction, so a directory listing is an index.
    name = os.path.basename(path)
    match = FILENAME_RE.match(name)
    if not match:
        report.fail(where, "filename must be 0xNNNN-<smsg|cmsg>-<lower-kebab>.yaml")
    else:
        if int(match.group(1), 16) != fiche["id"]:
            report.fail(where, f"filename opcode 0x{match.group(1)} != id {fiche['id']:#06x}")
        if DIRECTIONS.get(fiche["direction"]) != match.group(2):
            report.fail(where, "filename direction does not match 'direction'")

    if fiche["direction"] not in DIRECTIONS:
        report.fail(where, f"direction must be one of {sorted(DIRECTIONS)}")
    if fiche["status"] not in STATUSES:
        report.fail(where, f"status must be one of {STATUSES}")
    if fiche["evidence"] not in LEVELS:
        report.fail(where, f"evidence must be one of {LEVELS}")

    for build in fiche["client_builds"] or []:
        if build not in known_builds:
            report.fail(where, f"client_builds references unknown build '{build}'")

    for dataset in fiche.get("client_datasets") or []:
        if dataset not in known_datasets:
            report.fail(where, f"client_datasets references unknown dataset '{dataset}'")

    # Every graded item carries a level, and the fiche is the weakest of them (EVIDENCE.md).
    levels = []
    for item_path, level in graded_items(fiche):
        if level is None:
            report.fail(where, f"{item_path} has no 'evidence' level")
        elif level not in LEVELS:
            report.fail(where, f"{item_path} has invalid evidence '{level}'")
        else:
            levels.append(level)
    if levels and fiche["evidence"] in LEVELS:
        weakest = min(levels, key=rank)
        if fiche["evidence"] != weakest:
            report.fail(where, f"evidence is {fiche['evidence']} but weakest field is {weakest}")

    # Provenance has to be followable: a level and where it came from.
    provenance = fiche["provenance"] or []
    if not isinstance(provenance, list) or not provenance:
        report.fail(where, "provenance must be a non-empty list")
    else:
        for index, entry in enumerate(provenance):
            if not isinstance(entry, dict):
                report.fail(where, f"provenance[{index}] is not a mapping")
                continue
            if entry.get("level") not in LEVELS:
                report.fail(where, f"provenance[{index}].level must be one of {LEVELS}")
            if not entry.get("source"):
                report.fail(where, f"provenance[{index}] has no 'source'")

    # A field claimed at L3+ needs provenance that actually reaches that level.
    best_provenance = max((rank(e.get("level")) for e in provenance
                           if isinstance(e, dict)), default=-1)
    for item_path, level in graded_items(fiche):
        if rank(level) >= rank("L3") > best_provenance:
            report.fail(where, f"{item_path} claims {level} but no provenance entry reaches L3")

    # ADR 0005: do not re-document the standard protocol. Ascension may reuse a standard
    # opcode number for something else, but that has to be stated, not implied.
    if fiche["id"] in baseline and not fiche.get("reuses_standard_opcode"):
        report.fail(where, f"opcode {fiche['id']:#06x} is {baseline[fiche['id']]} in "
                           "AzerothCore; set 'reuses_standard_opcode: true' with a note "
                           "if Ascension repurposed it, otherwise this fiche is redundant")
    if fiche.get("reuses_standard_opcode") and fiche["id"] not in baseline:
        report.fail(where, "'reuses_standard_opcode' set but the opcode is not in "
                           "AzerothCore's table")

    # ADR 0004: a fact read from client source is true of a snapshot, not of "the client".
    if any(level == "L2" for _, level in graded_items(fiche)) and not fiche.get("client_datasets"):
        report.fail(where, "a field graded L2 requires 'client_datasets' naming the snapshot "
                           "it was read from")

    # ADR 0003: an address that is still absolute cannot support a proven fiche.
    for item_path, symbol in client_symbols(fiche):
        if not isinstance(symbol, dict):
            report.fail(where, f"{item_path} is not a mapping")
            continue
        if not symbol.get("rva") and not symbol.get("address_observed"):
            report.fail(where, f"{item_path} has neither 'rva' nor 'address_observed'")

    if fiche["status"] == "proven":
        replay = fiche.get("replay")
        if not isinstance(replay, dict) or not replay.get("script"):
            report.fail(where, "status 'proven' requires replay.script")
        else:
            script = os.path.join(root, replay["script"])
            if not os.path.isfile(script):
                report.fail(where, f"replay.script '{replay['script']}' does not exist")
            if not replay.get("asserts"):
                report.fail(where, "replay has no 'asserts'")
        if fiche["evidence"] != "L5":
            report.fail(where, "status 'proven' requires evidence L5")
        for item_path, symbol in client_symbols(fiche):
            if isinstance(symbol, dict) and not symbol.get("rva"):
                report.fail(where, f"{item_path} must carry an 'rva' before the fiche is proven")
    elif fiche["evidence"] == "L5":
        report.fail(where, "evidence L5 requires status 'proven'")


def main():
    parser = argparse.ArgumentParser()
    default_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    parser.add_argument("--root", default=default_root)
    args = parser.parse_args()
    root = os.path.abspath(args.root)
    report = Report()

    known_builds = load_ids(os.path.join(root, "client", "builds.yaml"),
                            "builds", report, "client/builds.yaml")
    known_datasets = load_ids(os.path.join(root, "client", "datasets.yaml"),
                              "datasets", report, "client/datasets.yaml")
    baseline = load_baseline(os.path.join(root, "protocol", "known-baseline.yaml"), report)

    opcodes_dir = os.path.join(root, "protocol", "opcodes")
    paths = sorted(os.path.join(opcodes_dir, n)
                   for n in os.listdir(opcodes_dir)) if os.path.isdir(opcodes_dir) else []
    fiches = [p for p in paths if p.endswith((".yaml", ".yml"))]

    seen = {}
    for path in fiches:
        with open(path, encoding="utf-8") as handle:
            try:
                fiche = yaml.safe_load(handle)
            except yaml.YAMLError as error:
                report.fail(os.path.relpath(path, root), f"invalid YAML: {error}")
                continue
        check_fiche(path, fiche, known_builds, known_datasets, baseline, root, report)
        if isinstance(fiche, dict) and "id" in fiche:
            key = (fiche["id"], fiche.get("direction"))
            if key in seen:
                report.fail(os.path.relpath(path, root),
                            f"duplicate opcode, already defined in {seen[key]}")
            seen[key] = os.path.relpath(path, root)

    if report.errors:
        for error in report.errors:
            print(f"error: {error}", file=sys.stderr)
        print(f"\n{len(report.errors)} error(s) in {len(fiches)} fiche(s)", file=sys.stderr)
        return 1

    print(f"{len(fiches)} fiche(s) valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
