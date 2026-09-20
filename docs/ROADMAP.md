# Roadmap

A milestone is done when its exit criterion is demonstrably met, not when its tasks look
finished. Completed items are ticked, never deleted.

## P0 — Foundations

**Exit criterion:** a fiche can be written and mechanically validated.

- [x] Repository, `README`, `CONTRIBUTING`, `CHANGELOG`
- [x] `docs/EVIDENCE.md` — the evidence ladder, normative
- [x] `docs/METHOD.md` — the investigation loop
- [x] ADR 0001, 0002, 0003
- [x] Fiche schema and linter, wired into CI
- [x] First fiche (`0x0726`), graded honestly as it stands today
- [x] Extract the client corpus (Ascension UI source; referenced not vendored, ADR 0006)
- [x] Populate `protocol/enums/` from the extracted Lua — 93 enums with file and line
- [x] Pin the client builds in `client/builds.yaml` (hash + ImageBase + patch delta)
- [x] Scope rule against re-documenting AzerothCore: `protocol/known-baseline.yaml`, ADR 0005
- [x] Data-snapshot axis: `client/datasets.yaml`, `dbcinfo.py`, ADR 0004
- [x] Register `ascension-live-2026-09-17` and `cointhrow-2026-09-09` with their delta

## P1 — Lab

**Exit criterion:** one fact reaches `L5` with a green replay script.

Most of this already existed in `coa-server-guide` and is reused rather than rebuilt; the
decrypting proxy was dropped because we own both ends (ADR 0007).

- [x] Lab client under Proton — `coa-client-lab` (`start`, `login`, `chat`, `screenshot`)
- [x] Probe addon (level A) — `CoaProbe`, answers as JSON through a SavedVariable
- [x] `ca` probe command: `IsKnownID`, `GetTalentRankByID`, active spec, AE/TE investment,
      and a `shim` flag saying whether the CoA compat override is loaded
      (`coa-server-guide` 58d1dd8, 82 tests pass)
- [x] ~~Decrypting proxy~~ — dropped, ADR 0007
- [x] Replay script written: `tools/replay/0x0726_flag_gate.py` (exits 2, inconclusive,
      until the forge command exists)
- [x] Packet forge — **already in AzerothCore**: `.debug send opcode` reads `opcode.txt`
      from the worldserver's working directory. No server change, no branch, no rebuild.
      File delivery verified with `docker cp` against slot 1.
- [x] Shim exposure measured per function rather than assumed per client (ADR 0007)
- [x] First `tools/replay/` script **green** — `0x0726` container semantics and the u8
      lock flag, run on slot 1 on 2026-09-19
- [ ] Stock `patch-B.MPQ` run, once the stock client can reach a localhost realmlist
      (its `GlueXML/RealmList/RealmList.lua` is one of the CoA patch's changes)

This milestone is the one that changes the project's nature. Everything before it
produces hypotheses; everything after it produces specification.

## P2 — Census

**Exit criterion:** we know what we do not know.

- [x] **Opcode table recovered, with its numbering**: 2 517 opcodes from the stock
      `Extensions.dll`, 2 059 named, via the opcode-name switch and its jump table.
      `tools/extract/opcode_names.py`, no disassembler needed. See
      `client/symbols/ascension-extensions-2026-08-13/opcodes.md`
- [x] `#4030`'s three opcode identities confirmed exactly; an earlier doubt of ours,
      raised from the wrong table, retracted in the same file
- [x] **Handler registration path** decoded: 532 registrations, `push handler; push
      opcode; call register`. `tools/extract/opcode_handlers.py`. It shows an entire
      unnamed block (`0x071f`–`0x072d`) is the Character Advancement service with real
      handlers, that `0x0900` has none, and it re-derives one of `#4128`'s published
      addresses independently. See `client/symbols/.../handlers.md`
- [x] `SMSG 0x0726`'s handler and record layout disassembled: struct offsets, the
      `+0x11..+0x17` hole, and why the packet cannot carry a rank. `objdump` sufficed;
      see `client/symbols/.../0x0726-handler.md`
- [x] Lua API bindings recovered: 1 229 name → implementation pairs,
      `tools/extract/lua_bindings.py`
- [x] The rank's reader located: `GetTalentRankByID` reads a **separate** container of
      `0x2c`-byte records, rank at `+0x0c`, not the `0x0726` container. See
      `client/symbols/.../rank-source.md`
- [x] The rank's real reader found by decompilation: the advancement service's getter at
      RVA `0x00152920`, stride `0x20`, key at `+0x04`, **rank at `+0x08`** — the same
      shape `0x0726` sends. The earlier "this packet cannot carry a rank" is withdrawn
- [x] The handler confirms `+0x08` is the rank and `+0x04` the key, and calls the same
      getter the reader does — so it is **not** two different vectors
- [x] **Settled without another lab run.** One vector, key at `+0x04`, three accessors:
      membership, rank at `+0x08`, lock byte at `+0x10`. `IsLockedID` matched the raw
      entry id in the same forged record that `GetTalentRankByID` answered `0` for, so the
      record is stored and keyed correctly and only that one binding is broken — it passes
      `*(catalogue_entry + 0)` instead of the id
- [x] **Resolved.** The `0x2c` store is the **Wildcard** store: its `push_back`
      (`FUN_10a30260`) is the registered handler for `SMSG_WILDCARD_ENTRY_LEARNED`
      (`0x0621`). `GetTalentRankByID` asks it first, finds it empty outside Wildcard mode,
      and falls back to the talent store keyed on `*(catalogue_entry + 0)` — not the entry
      id. `0x0726` stores the rank correctly; the client cannot read it back
- [x] Ghidra headless pipeline (`tools/ghidra/ghidra.sh`, both binaries imported; scripts
      under `tools/ghidra/scripts/`)
- [x] `Ascension.exe` read for the wire path: loader patch, the DLL's own patch and
      detours, `ClientServices` dispatch and send, `CDataStore` — `client/wire-path.md`;
      the CoA exe patch delta recorded
- [x] A stub fiche per custom opcode: **752** generated by
      `tools/codegen/stub_fiches.py` from the opcode table, the handler map and the UI
      corpus — 117 carry the UI files that name their event, 45 are flagged
      `reuses_standard_opcode` because AzerothCore uses that number for something else
- [x] **Layout skeletons recovered mechanically**: `tools/extract/packet_layout.py` reads
      each handler's cursor arithmetic and recovers the field widths in order — 346 of 532
      handlers, merged into 329 fiches. Validated against four independently known layouts
      (`0x0725`, `0x0726`, `0x0926`, `0x06E5`)
- [x] `protocol/INDEX.md`, generated, so 753 fiches are navigable
- [x] Ghidra reproducibility: scripts in `tools/ghidra/scripts/`, wrapper
      `tools/ghidra/ghidra.sh`, project in `build/ghidra/`, runbook section. Every
      decompilation-based fact now names a script and an address
- [x] Fiches for the 19 handled-but-unnamed opcodes (the Character Advancement block
      `0x071f`–`0x072d` included) and a hand-written one for `0x0727`
- [x] Third leg of usage: `tools/extract/server_usage.py` reads `mod-ascension-compat` —
      70 opcodes, written into 68 fiches as `used_by_server:`
- [x] **The `#4027` check, run against the current server**: `tools/extract/server_layout.py`
      diffs what `mod-ascension-compat` writes against what the client reads. **No server-side
      layout bug found** across the 16 packets it writes; nine verified by hand against the
      decompiled handler. See `client/server-layouts.md`
- [x] Fields **named** on those nine (`0x0725`, `0x0673`, `0x06BA`, `0x0769`, `0x0770`,
      `0x0771`, `0x076F`, `0x075E`, plus `0x0726`): widths `L3` from the decompiled handler,
      names `L1` from the server's own serializer
- [x] Appearance and vanity-collection packets named too: **all 16 packets the server
      writes are now verified against the decompiled handler and carry named fields**
- [x] Manastorm resolved too — its `enum Opcode` and the `SendResult` helpers — bringing
      the check to **27 server-written packets, 27 verified, 0 wrong**, 28 fiches named
- [x] Every unattributed construction classified: two `SendResult` helpers (four opcodes,
      all one string), seven copies of incoming packets, one test harness. **29 server-
      written packets, 29 verified, nothing left unattributed**
- [x] **The client-to-server direction**: twelve senders located and read through the
      `CDataStore` pointer table (`PutData(ptr, size)` gives the width). Nine packets the
      server parses agree with its reader; `0x0523` and `0x09C7`, which the server only
      logs, now have a client-side layout. See `client/client-senders.md`
- [x] `tools/extract/client_sender.py`: the `push`/`PutData` reading, automated and
      validated against the twelve hand-read senders, then extended with the two wrapper
      helpers — **158 of 203** custom CMSGs get a client-side layout (59 clean, 43 prefix
      behind a helper, 56 empty); two more are query-service request/response pairs.
      Corrected 2026-09-19: `DAT_10bc90cc` is `Put(u32)`, not an opcode-only write
- [x] The recovery service's twelve opcodes (six categories × query/recover) read by hand
      from the shared switch tail; `0x0682`/`0x0684` are the unnamed worldforged pair
- [x] The 45 CMSGs the scan cannot follow, accounted for: twelve recovery-service and
      two draft-toggle opcodes read by hand (computed or switch-selected), four "sites"
      that are data bytes inside `.text`, two stock 3.3.5a opcodes, and **33 with no trace
      of the opcode anywhere in the build** — read as having no sender in this build
      (`client/client-senders.md`)
- [x] `CreatePacket`/`Send`/`RegisterPacket` verified from an insecure addon on slot 1
      (2026-09-19): the binary's own Lua packet API is the replay channel (ADR 0008,
      `client/lua-packet-api.md`); CoaProbe `pksend`/`pkwatch`/`pkfind`/`pkmeta`
- [x] String literals referenced by each of the 532 handlers (`HandlerStrings.java`),
      merged into the fiches as `client_strings:` — the event names the handler fires
- [x] Event arguments from the UI (`event_args.py`, 374 events) joined to the fiches as
      `client_events:` — 101 fiches now show what Lua receives next to what the handler
      reads. See `client/handler-events.md`
- [x] What each handler fires (`handler_fire.py`): event, format, helper, and the read
      filling each position for 56 firings — `client_fire:` in 179 fiches; three layouts
      named by the triple agreement, the rest need a reader
- [x] Name the skeleton layouts opcode by opcode, handler decompilation next to
      `client_events`, `client_fire`, `client_binding` and the server's readers/writers.
      State on 2026-09-20: **456 named, 7 proven, 48 empty** (opcode alone), 188 still
      `widths` -- 187 of them the `SMSG_PATCH_*` row family, whose fields are DBC columns
      the atlas has no names for (`client/patch-tables.md`), plus `0x05B1`, where the
      server and client disagree (`client/server-layouts.md`). The 73 `unknown` are
      names with no client code behind them. Where a handler reads through a helper the
      fiche says how far the reading went ("not followed") instead of guessing. Three
      extractor gaps recurred and are recorded on the fiches: a leading string the width
      scan missed (result packets, senders), a packed guid read through the exe
      (`0x0761`-`0x0766`), and both branches of a GM/player split counted twice
- [x] Floats recovered (`movss`), which reproduces `#4128`'s `0x09BC` layout field for
      field across its first nine
- [x] Strings partly recovered (pointer-at-cursor idiom), 22 fiches — not all of them, so
      a missing `cstring` proves nothing
- [x] A fiche for every custom opcode the client names, handles or sends (775); `MSG_NULL`,
      `MAX` and `UMSG_*` excluded as non-wire; coverage state explicit per fiche
      (`protocol/COVERAGE.md`)
- [ ] Frida hooks (level B) operational

## P3 — Retro-audit

**Exit criterion:** the `#4027` debt is settled.

- [x] One fiche per wire claim already shipped by `azerothcore-wotlk-coa#4027` and `#4128`
      (`docs/retro-audit.md`)
- [x] Each graded against the ladder; two `#4128` claims withdrawn, the rest confirmed
- [x] Nothing shipped was below `L3` once read; the one wrong belief is recorded and was
      posted on the PR. The core's `ascension-talents.md` correction is a server-repository
      change, listed as still owed
- [ ] `CoinThrow`'s opcode notes and capture provenance requested and, if shared, integrated
- [ ] Ask `CoinThrow` for the `Extensions.dll` SHA-256 and ImageBase of the install that
      produced `cointhrow-2026-09-09` — it would convert his published addresses to RVA

## P4 — Character Advancement vertical

**Exit criterion:** the native advancement path is specified end to end.

- [x] `0x0651`/`0x0652`, `0x0665`/`0x0666`, `0x0689`/`0x068A` — the Manastorm enter, leave and
      set-slot pairs at `L5` (`tools/replay/manastorm_roundtrip.py --pair all --control`),
      each with a size-check control; six fiches proven
- [x] `0x0725`, `0x0726`, `0x0727` measured (`tools/replay/0x0726_flag_gate.py`,
      `tools/replay/ca_vertical.py`, 2026-09-19): `0x0725`'s slot fires the spec event with
      slot + 1; `0x0726`'s count, entryId and lock byte are `L5` (marker, buildTime and
      reserved stay `L1`, so the fiche is not proven as a whole); `0x0727`'s server reader is
      `L5` through `pksend`, its client sender stays `L3`. Found on the way: a Lua
      `RegisterPacket` replaces the native handler until the client restarts
      (`client/lua-packet-api.md`)
- [x] `0x0926` credits proven (`L5`, `ca_vertical.py --check credits`)
- [ ] `0x09D0` / `0x09BC` / `0x06E5` realm cluster — `0x09BC`'s realmId, expansion, maintenance and
      auctionCutRate are `L5` (`ca_vertical.py --check realm`); its other 16 fields have no getter
      to read them back and stay `L3`; `0x09D0` and `0x06E5` untouched
- [ ] `SMSG_COA_CONFIG` (`0x0900`) at `L5`
- [ ] `ChrClassesRoles` rows at `L5`
- [ ] The native purchase validator resolved — why `ApplyPendingBuild` refuses a build

## P5 — Integration

**Exit criterion:** documentation and shipped code cannot diverge.

- [x] `tools/codegen/emit.py` emits `generated/ascension_opcodes.h` (with layout state, evidence and
      the server's alias per opcode)
- [ ] `mod-ascension-compat` consumes the generated header (a change in the server repository)
- [x] `generated/ascension_opcodes.go` for the Ghost harness
- [x] `generated/ascension.lua`: a Wireshark dissector for plaintext-header captures, decoding
      the widths the atlas holds
- [x] `tools/replay/run_all.py --slot N` runs every replay and writes `docs/lab-runs/<date>.md`;
      `--update-fiches` rewrites `last_run` and names the demotions a FAIL requires

## P6 — Publication

**Exit criterion:** a third party can verify our claims without asking us.

- [x] `site/` (`tools/codegen/site.py`): one Markdown page per fiche plus the index, served
      as-is by GitHub Pages once the repository is public
- [ ] Repository made public
- [ ] Call for archived `.pkt` sniffs and client builds — partly answered: CoinThrow's
      2026-09-20 reference is taken from a live session, but the capture itself is not shared,
      so it stays `L1` here. Their document is deliberately **not** in this repository
- [x] Cross-check with `CoinThrow` — 65 opcodes compared field by field in
      `docs/crosscheck-cointhrow-2026-09-20.md`: broad agreement, eight conflicts listed, and
      `0x0674`'s record closed by their side. Two conflicts (`0x0672`, `0x06CA`) were re-read
      here and the handler's order stands
- [ ] Name the `SMSG_PATCH_*` rows through the route that cross-check opened: the client's own
      Lua builders (addresses in their reference, decompiled here = `L3`) and the community
      repack's `*_dbc` schema checked against our client DBC headers (= `L2`)
