# Contributing

## Ground rules

**Document the custom surface only.** AzerothCore already implements the standard 3.3.5a
protocol and loads the standard DBC set; Blizzard's FrameXML is public. Re-describing any
of it is wasted work and a second source of truth. The linter refuses a fiche for an
opcode the core already defines (ADR 0005) — if Ascension repurposed that number, say so
with `reuses_standard_opcode: true` and a note.

**State the evidence level, or do not state the fact.** A contribution that says "I am fairly
sure this field is padding" is welcome. A contribution that says "this field is padding"
without saying how that was established is not, however correct it turns out to be.

## Environment

```sh
python3 -m pip install --user pyyaml
python3 tools/lint/lint_fiches.py          # the schema
python3 tools/codegen/coverage.py          # CI fails if COVERAGE.md / atlas.json are stale
./tools/regenerate.sh <client dir> <core>  # before a tooling change: must leave git clean
```

The linter is the schema. There is no separate JSON Schema to keep in sync — see ADR 0002.
Generated files say so on their first line; change the generator, not the output. A hand
fiche says "Regenerating the atlas leaves this file alone" and is never touched by the
merges (they only fill stubs with `status: unknown`).

## Adding or changing a fiche

1. Read `docs/EVIDENCE.md` and `docs/METHOD.md`. They are normative, not background.
2. Copy an existing fiche from `protocol/opcodes/` as a starting point.
3. Filename: `0xNNNN-<direction>-<lower-kebab-name>.yaml`, e.g.
   `0x0726-smsg-character-advancement-known-entries.yaml`. Unknown name: use
   `0xNNNN-smsg-unknown.yaml` and rename when it is identified.
4. Grade **every field**, not just the fiche. The fiche's level is the minimum of its
   fields; the linter enforces that.
5. Every level at `L3` or above needs a matching `provenance` entry a reader can follow:
   an RVA and a build, a capture path, or a replay script.
6. `status: proven` requires a replay script that exists and RVAs (not raw absolute
   addresses) on every symbol.
7. Name your sources of truth: `client_builds:` always, and `client_datasets:` as soon as
   any field is graded `L2`. A catalogue fact without its catalogue is not reproducible
   (ADR 0004); the linter enforces it.
8. Keep the provenance of wrong beliefs. When a claim turns out false, leave it in
   `provenance` with a note saying so. That history is the reason this repository exists.

## Grading someone else's claim

A claim from another pull request, issue or repository is `L1` here, even when its author
states they verified it in game. We grade what *we* can reproduce. When their evidence is
shared and we re-derive the fact, it moves up; when their notes are private, the fiche
records that as the reason it is stuck.

This is not a judgement about anyone's work. It is what makes the atlas a specification
rather than a collection of assertions.

## What must never be committed

MPQ archives, DBC data files, `Extensions.dll`, client executables, or any other
redistributable game asset. CI rejects them. Commit the *observation* — a layout, a
symbol table, a trace — never the artifact it came from.

Bytes captured by a replay (a `pkwatch` record) belong in the fiche's `asserts_measured`,
with the date, build and slot in `last_run`; there is no capture directory.

## Commits and history

- [Conventional Commits](https://www.conventionalcommits.org/). `docs:` for a fiche,
  `feat:` for tooling, `fix:` for a corrected fact.
- Documentation and code live in the same commit. A tool that changes a layout and does
  not update the fiche is incomplete.
- A structural decision produces an ADR in `docs/adr/` in the same commit as the change.
  ADRs are never rewritten; a reversed decision gets a new ADR that supersedes the old one.
- Update `CHANGELOG.md` under `Unreleased` whenever a fact changes level.

## Review

A fiche review asks three questions, in this order:

1. Is each field's level *honest* — not optimistic, not falsely modest?
2. Can a reader follow the provenance to the evidence without asking the author?
3. If it claims `proven`, does the replay script actually run?

Everything else is secondary.
