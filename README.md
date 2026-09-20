# CoA Protocol Atlas

The Ascension 3.3.5a custom protocol, rebuilt from the client and graded by evidence.
One YAML fiche per opcode, the `Extensions.dll` symbol tables they rest on, the UI corpus
facts that name them, and the lab tooling that proves them.

**772 opcodes documented** (every custom opcode the client names, plus the unnamed ones
it handles or sends), each with an explicit statement of what is known and what is not:
`protocol/COVERAGE.md`. Start there, or with `tools/atlas.py`.

## Ten-second use

```sh
python3 -m pip install --user pyyaml
tools/atlas.py lookup 0x0726                  # one opcode: status, layout, handler, events, replay
tools/atlas.py lookup SMSG_ENTER_MANASTORM_RESULT
tools/atlas.py search manastorm               # names, summaries, events, string literals
tools/atlas.py list --dir s2c --layout unknown # what is still unread
tools/atlas.py coverage                       # the counts
```

`protocol/atlas.json` is the same data for programs (one object per fiche, sorted by
opcode); `protocol/INDEX.md` and `protocol/COVERAGE.md` are the human tables.

## What a fiche says

`protocol/opcodes/0x0652-smsg-enter-manastorm-result.yaml`, abridged:

```yaml
id: 0x0652
name: SMSG_ENTER_MANASTORM_RESULT
direction: server_to_client
status: proven                 # unknown | hypothetical | proven
evidence: L5                   # the minimum over the fields
layout:
  - { name: result, type: cstring, evidence: L5 }
client:
  handler: { rva: "0x002a1a10", evidence: L3 }     # in Extensions.dll, build-bound
client_strings: ["ENTER_MANASTORM_RESULT", ...]  # literals the handler references (L3)
client_events:                                    # what the UI's Lua receives (L2)
  - { event: ENTER_MANASTORM_RESULT, args: [resultStrKey] }
client_fire:                                      # what the handler fires, decompiled (L3)
  - { event: ENTER_MANASTORM_RESULT, format: "%s", helper: FUN_100b9620 }
used_by_server: { files: [modules/mod-ascension-compat/src/AscensionManastormProtocol.h] }
provenance: [...]                                 # one entry per claim, with its level
replay: { script: tools/replay/manastorm_roundtrip.py, last_run: {...} }
```

Every field carries an **evidence level** — `docs/EVIDENCE.md`, normative:

| | | |
| --- | --- | --- |
| `L0` | conjecture | |
| `L1` | someone else's archive, PR or notes | `#4027` shipped on this |
| `L2` | the client's own Lua, XML, DBC | names, enums, event arguments |
| `L3` | disassembly of `Extensions.dll`, RVA recorded | layouts, handlers, senders |
| `L4` | capture of a real realm | none exist; the realms are gone |
| `L5` | replayed against the lab client by a committed script | `tools/replay/` |

Rules that follow: no server code on a fact below `L3`; anything below `L5` shipped to
production is declared in the pull request; every `L5` fact has a replay script. The
linter (`tools/lint/lint_fiches.py`) is the schema and enforces the grading.

## Why

`azerothcore-wotlk-coa#4027` shipped `SMSG 0x0726` with fields written as zero, from an
archive layout never put in front of the client; the packet was accepted and ignored.
Nothing in the process separated *"read somewhere"* from *"proven against the client"*.
This repository is that separation, and the `L1` entry on the `0x0726` fiche stays as the
reason.

## How the facts are made

```
Extensions.dll ---- tools/extract (objdump idioms) --> client/symbols/<build>/*.yaml
               \--- tools/ghidra  (decompilation) --/          |
patch-B.MPQ    ---- tools/extract (UI corpus)     --> protocol/enums, client/event-args.yaml
core checkout  ---- tools/extract                 --> protocol/known-baseline.yaml, client/server-*.yaml
                                                             |
                                       tools/codegen (stubs + merges)   -->  protocol/opcodes/*.yaml
                                                             |
                                       tools/replay + lab client        -->  status: proven, L5
```

`tools/regenerate.sh <client dir> <core checkout>` re-runs the whole chain and fails if the
repository does not reproduce byte for byte; CI runs the linter, the coverage check and the
asset guard. The lab side — slot, client, CoaProbe, the Lua packet API that makes replays
possible — is in `docs/RUNBOOK.md` and `client/lua-packet-api.md`.

## Where things are

| Path | Contents |
| --- | --- |
| `protocol/opcodes/` | the fiches — the product |
| `protocol/COVERAGE.md`, `protocol/atlas.json`, `protocol/INDEX.md` | generated views of the fiches |
| `protocol/enums/` | enums lifted from the UI's Lua, with file and line |
| `protocol/known-baseline.yaml` | what AzerothCore already implements — never re-documented (ADR 0005) |
| `client/symbols/<build>/` | opcode names, handlers, layouts, senders, Lua bindings, strings, fire formats |
| `client/*.md` | the readings: `wire-path.md` (exe ↔ DLL: loader, detours, `CDataStore`), `server-layouts.md` (server vs client), `client-senders.md`, `handler-events.md`, `patch-tables.md` (the `SMSG_PATCH_*` family), `lua-packet-api.md` |
| `client/builds.yaml`, `client/datasets.yaml`, `client/corpus.yaml` | the identity of every binary, DBC snapshot and UI archive facts are bound to |
| `generated/` | `ascension_opcodes.h`, `ascension_opcodes.go`, `ascension.lua` (Wireshark) — emitted from the fiches |
| `site/` | one Markdown page per fiche plus an index, for GitHub Pages |
| `tools/` | `extract/`, `ghidra/`, `codegen/`, `replay/` (incl. `run_all.py`), `lint/`, `atlas.py`, `regenerate.sh` |
| `docs/` | `EVIDENCE.md`, `METHOD.md`, `RUNBOOK.md`, `ARCHITECTURE.md`, `ROADMAP.md`, `retro-audit.md`, `lab-runs/`, `adr/` |

## Scope

Ascension's custom surface only: opcodes, layouts, `Extensions.dll` symbols, UI
constants. Not the standard 3.3.5a protocol (AzerothCore has it), not Blizzard's FrameXML,
not the server implementation (`azerothcore-wotlk-coa` implements; this describes). No game
asset is ever committed — MPQ, DBC, DLL, EXE — and CI rejects them; the repository holds
observations and tools.

## Working on it

`AGENTS.md` is the operating manual (commands, rules, pitfalls) for a person or an agent.
`CONTRIBUTING.md` covers adding a fiche and grading a claim. `docs/ROADMAP.md` says what is
done and what is next; `CHANGELOG.md` records every change of evidence level.
