# Architecture

A database of facts about a binary protocol, the machinery that derives them from the
client, and the machinery that proves them against a running client. Three layers, all of
them present in the repository as described here — nothing below is planned.

```
  Extensions.dll (stock)        patch-B.MPQ (UI)          azerothcore-wotlk-coa
        |                             |                            |
  tools/extract/*.py           tools/extract/               tools/extract/
  (objdump idioms)             extract_ui, lua_enums,       ac_baseline, server_usage,
  tools/ghidra/*.java          event_args                   server_layout
  (decompilation)                    |                            |
        v                            v                            v
  client/symbols/<build>/      protocol/enums/            protocol/known-baseline.yaml
  opcodes, handlers, layouts,  client/event-args.yaml     client/server-usage.yaml
  senders, lua-bindings,       client/corpus/             client/server-layouts.yaml
  handler-strings, handler-fire
        \                            |                            /
         +--------------- tools/codegen (stub_fiches, merge_*) --+
                                     |
                                     v
                         protocol/opcodes/*.yaml   <---- hand edits (status: hypothetical)
                                     |
                +--------------------+---------------------+
                v                    v                     v
        tools/codegen/index   tools/codegen/coverage   tools/replay/*.py + lab client
        INDEX.md              COVERAGE.md, atlas.json  status: proven, L5
```

## The fact database: `protocol/`

One YAML fiche per opcode. Human-readable and machine-readable on purpose: the same file
is the documentation and the export input, so they cannot drift. `known-baseline.yaml` is
what AzerothCore already implements; the linter refuses a fiche that duplicates it
(ADR 0005). `enums/` are lifted from the UI's Lua with file and line. `INDEX.md`,
`COVERAGE.md` and `atlas.json` are generated views.

## Identity: `client/`

A fact about a binary is true for a build; `client/builds.yaml` names and hashes each
(ADR 0003) and `client/symbols/<build>/` holds what was read out of it. A fact from a
catalogue is true for a data snapshot (`client/datasets.yaml`, ADR 0004); a fact from UI
source for a corpus (`client/corpus.yaml`, ADR 0006). The DBC files, MPQ archives and
binaries stay outside the repository; only manifests and lifted facts are committed.

The prose readings live next to the tables: `server-layouts.md` (every packet the CoA
server writes, checked against the client's handler), `client-senders.md` (every packet
the client writes), `handler-events.md` (handler → event → Lua arguments),
`lua-packet-api.md` (the replay channel).

## The machinery: `tools/`

| Directory | Role |
| --- | --- |
| `extract/` | one script per source: PE identity (`peinfo`), opcode names, handlers, packet layouts, senders and Lua bindings from `Extensions.dll`; UI corpus, enums and event arguments from the MPQ; baseline, server usage and server layouts from the core checkout; handler fire formats from Ghidra's C |
| `ghidra/` | `ghidra.sh` (headless wrapper, project in `build/ghidra`) and the scripts a fiche may cite: `Decomp`, `DecompAt`, `Refs`, `Callers`, `HandlerStrings`, `SenderC`, `DumpC` |
| `codegen/` | `stub_fiches` opens a fiche per opcode; `merge_*` write layouts, senders, usage, strings, events and fire formats into fiches idempotently; `index` and `coverage` render the views |
| `replay/` | one executable per `L5` fact; prints PASS, FAIL or INCONCLUSIVE |
| `lint/` | the fiche schema and the asset guard, both run in CI |
| `atlas.py`, `regenerate.sh` | the query CLI and the reproducibility gate |

## The oracle

The official realms are gone, so the client is the specification: it accepts a correct
packet and rejects a wrong one, and it can be asked what it did. The loop (ADR 0007, 0008):

- **server → client**: AzerothCore's `.debug send opcode` forges any packet from
  `opcode.txt`; CoaProbe's `pkwatch` (the client's own `RegisterPacket`) captures the
  bytes the handler receives; the UI is then asked what changed (`probe ca`, ...).
- **client → server**: CoaProbe's `pksend` (`CreatePacket` + `Put*` + `Send`) sends a
  layout; `pkwatch` captures the reply. This proves the server's reader, not the client's
  sender, and a fiche says which.

No proxy, no hooks, no binary patch. CoaProbe and `coa-client-lab` live in `coa-server-guide`.

## Verification

- **CI, every push:** fiche lint, coverage/export freshness, asset guard, whitespace.
- **`tools/regenerate.sh`, before a tooling commit:** the whole chain, then `git status`
  must be clean — the repository reproduces from its sources.
- **Lab run, by hand:** `tools/replay/*.py` on a claimed slot. A failing replay demotes
  the fact out of `L5` in the same commit.
