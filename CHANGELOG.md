# Changelog

All notable changes to this project are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: [SemVer](https://semver.org/).

A discovery is a change: when a fact changes evidence level, say so here.

## [Unreleased]

### Added

- `tools/replay/ca_vertical.py`: the Character Advancement vertical at `L5` — credits
  (`0x0926`, proven), realm info (`0x09BC`, four fields), active spec (`0x0725`, slot + 1 in
  the event) and the known-entries upload (`0x0727`, the server's reader) — and
  `docs/lab-runs/`, the `run_all.py` reports (2026-09-19: the runs the probe's own packet
  watch broke; 2026-09-20: all green).
- `client/lua-packet-api.md`: `RegisterPacket` replaces the client's own handler for that
  opcode until the process restarts, and `ClearPacket` does not restore it (decompiled and
  measured). ADR 0008 and the runbook carry the consequence: watch the handler's event, not
  the packet, when the feature behind it is under test.

- `docs/crosscheck-cointhrow-2026-09-20.md`: 65 opcodes compared against a third party's
  live-session reference. That reference is someone else's work and is deliberately not
  committed here; only our comparison is.
- `tools/helper_trace.py`: prints a decompiled function's read cursor in source order.
- A second sweep over the 184 `SMSG_PATCH_*` rows, in seven shards by the naming source that
  exists for each, every shard verified by a skeptic. 183 fiches changed and the skeleton count
  falls from 178 to 104. Rows whose table AzerothCore already loads take their column names from
  the core at `L1`; rows named by the client's own Lua or by our binary take theirs at `L2` and
  `L3`; rows with no source anywhere now say that in words, with the geometry read from the DBC
  header, instead of staying an open question.
- The skeptics again found what the decoders missed: a missing trailing string in
  `ItemDisplayInfo` (fourteen calls to the string helper, not thirteen), a client-struct write
  in `TalentTab` sourced from a never-assigned local, a locale block described as sixteen
  columns wide in one sentence and seventeen in the next, five prose miscounts of "X of Y
  named", and two field notes in `APPEARANCES` and `SPELL_TAG_TYPES` that claimed a getter did
  not read a field when tracing its control flow shows it always does.
- A family sweep over the 122 opcodes that still had no layout outside the `SMSG_PATCH_*` rows:
  eight decoders, each followed by a skeptic whose only job was to refute what the decoder had
  just written. 95 fiches changed. Most turn out to be **dead opcodes** — a name in the client's
  table with no handler and no sender — which is a real answer and is now written as one
  (`layout: []  # empty`, status `unknown`) instead of an open question.
- The skeptics earned their place. They caught three systematic defects the decoders had
  introduced: a byte-scan count that did not reproduce and a provenance claim built on it
  (`0x074F`), a miscounted "1,348 standard opcodes" figure repeated across six fiches (it is
  1,306 stock plus 42 fork-only, two different fields of `known-baseline.yaml`), and a claim in
  fifteen fiches that a scan's hits sat in the crash reporter's string pool — the bytes are
  `(dword, dword)` pairs belonging to an x86 instruction-length-decode table, read directly.
  Every one was fixed in place rather than dropped.
- `client/patch-table-names.md`: every `SMSG_PATCH_*` row against the client DBC header it
  carries, with the naming source that exists for it — 11 rows named by the client's own Lua
  builders, 11 by a UI getter, 70 by AzerothCore's `DBCfmt.h`, and 141 with no source at all.
  It also records that the third party's "64 tables named by a repack schema" are all stock
  Blizzard tables the core already loads, so they name nothing for a CoA-custom table.
- Two fiches for numbers the capture reference covers and we had none for: `0x0900`, a real
  frame no client build handles, and `0x0023`, the first fiche here for a number AzerothCore
  already defines (`reuses_standard_opcode: true`, ADR 0005). Both carry their payload at `L1`;
  what is ours is the check that neither stock binary contains the strings reported on
  `0x0023`, so such a list has to arrive at runtime. `0x07FC` got no fiche: the reference
  retracts it as a slice of a zlib stream and our side finds nothing on the slot.
- `tools/ghidra/ghidra.sh` gains per-worker workspaces (`GHIDRA_WORKSPACE=<name>`) and a
  `farm <N>` verb. A Ghidra project locks exclusively, but a reflink copy of it costs 0.15 s
  and no disk, so work does not have to be serialised: 232 functions take 28 s on one worker
  and 16 s on four. Measured costs and the one caveat (workspaces drift apart in
  auto-generated symbol names, never in structure) are in `docs/RUNBOOK.md`.
- `tools/extract/lua_keys.py` and `client/symbols/<build>/lua-keys.yaml`: the Lua table keys
  the client's own builders set, with the record offset read after each — 22 builders, 234
  keys, read out of our binary, so a field name taken from them is `L3`.

### Fixed

- Two of the nine server/client disagreements in `client/server-layouts.md` were our own
  tooling reading itself wrong, and both are retracted: `0x05B1` (Ghidra runs one client
  function into the next past a noreturn `__fastfail`, and our server chain ran out of one
  writer into another) and `0x05AC` (an `AppendConfigString` whose argument is a call
  expression, a helper the extractor does not enter, and both branches of an `if`
  concatenated). Hand-tracing shows both sides agree field for field. A row in that table
  means "the two flat readings differ", never "the client and the server disagree".
- `0x0730`'s layout was a flattening of a parse helper's reads into a fixed struct; the
  packet is a list.

### Changed

- Layouts named across the board (2026-09-20): 456 fiches carry field names read from
  the decompiled handler or sender next to the UI's events and calls; 48 argument-less
  requests are marked empty; the `SMSG_PATCH_*` row family keeps its widths (DBC columns
  without offline names). Sender bindings Ghidra had merged with a neighbour are noted on
  the fiche (`0x0735`, `0x0626`/`0x0628`, `0x061D`).
- `0x0726`'s fiche records the lab runs that failed because of the probe's own packet
  watch, and that the handler accepts entries of any class.

- `protocol/COVERAGE.md` and `protocol/atlas.json` (`tools/codegen/coverage.py`): every
  fiche classified by client code (handler / sender / none) and layout state (proven /
  named / widths / empty / prefix / unknown); CI fails when they are stale.
- `tools/atlas.py`: `lookup`, `search`, `list`, `coverage` over `atlas.json`.
- `AGENTS.md` (operating manual; `CLAUDE.md` points at it).
- Second-source layouts: for 169 handlers whose read idiom `packet_layout.py` could not
  follow, the decompiled read sequence (`handler-fire.yaml`) supplies widths, marked as
  such in the fiche.

- `docs/retro-audit.md`: every wire claim of `#4027` and `#4128` with its current grade and standing.
- `site/` (`tools/codegen/site.py`): a Markdown page per fiche and an index for GitHub Pages.
- `tools/replay/run_all.py`: runs every replay against a slot and writes `docs/lab-runs/<date>.md`.
- `client/patch-tables.md`, `patch_tables.py`, `merge_patch.py`: the 114 custom DBC tables
  `Extensions.dll` keeps and, for 87 `SMSG_PATCH_*` fiches, which table's row the packet
  carries (`patches_table:`, the block copy named `row`).
- Loop structure in decompiled layouts: `handler_fire.py` nests the reads a handler makes
  inside a counted loop as `{repeat, reads}` and `merge_fire.py` renders them as `repeat`
  blocks (42 fiches); folded multi-field reads are split by their loads.
- Fourteen challenge and trial layouts read by hand (`tools/set_layout.py`).
- `client/wire-path.md`: how the exe loads the DLL (entry patch at `0x0040b7d0`), the
  DLL's installer (`FUN_102c3540`: the opcode bound at `0x0063200d` patched `0x51f` →
  `0x9d4`, five detours on `ClientServices`), the incoming dispatcher and the outgoing
  hook, the `CDataStore` object and its accessors (`client/symbols/ascension-exe-2010-06-25-stock/functions.yaml`,
  `exe-pointer-table.yaml`: 461 slots, 44 labelled), the three string idioms.
- `client/builds/coa-exe-rev4-2026-09-14.delta.md`: the CoA patch's seven changes to the exe.
- The server-layout check reaches `mod-coa-challenges` (54 opcodes, 46 agree, 9 explained),
  and `merge_server_names.py` lends the server's operand names where the sides agree.

### Changed

- `0x10bc90fc` is `CDataStore::Finalize`, not the send (`0x10bc91e8`/`ec` is); the sender
  layouts were not affected. `client/client-senders.md` says so.
- `known-baseline.yaml` now separates stock 3.3.5a opcodes (below `NUM_MSG_TYPES`) from the
  41 constants the CoA fork added (`fork_opcodes`, shown as `server_name` in `atlas.json`
  and in the generated header). The linter's duplicate check compared strings to ints and
  never fired; fixed. Four fiches for stock opcodes under Ascension spellings
  (`0x01E0`, `0x01FC`, `0x0291`, `0x049A`) are gone.
- `generated/`: `ascension_opcodes.h`, `ascension_opcodes.go` and a Wireshark
  `ascension.lua` emitted from the fiches (`tools/codegen/emit.py`), checked by CI.
- `README.md` and `docs/ARCHITECTURE.md` describe what exists; the placeholder
  directories for a proxy, Frida hooks, a pkt parser, captures and structs are gone
  (ADR 0007 and 0008 chose the Lua packet API instead).
- `stub_fiches.py` skips `MSG_NULL`, `MAX` and `UMSG_*` (table markers and
  client-internal messages, not wire opcodes).
- The repository is on GitHub (`lostmind84/coa-protocol-atlas`, private), branch `main`.

- `client/symbols/<build>/handler-strings.yaml` (Ghidra `HandlerStrings.java`): the string
  literals each of the 532 handlers references; `merge_strings.py` writes them into the
  fiches as `client_strings:` — 202 handlers reference at least one.
- The recovery service documented: twelve client-to-server fiches (`0x05D2`–`0x05E8`,
  `0x0682`, `0x0684`) from the two Lua bindings' shared switch; the UI's `WildCardRoll`
  category cannot be sent with this build.
- `tools/ghidra/scripts/SenderC.java`: the `CDataStore` calls in a sender's decompilation.
- `tools/extract/event_args.py` and `client/event-args.yaml`: the argument names the UI's
  Lua declares for 374 events; `merge_events.py` joins them to 101 fiches as
  `client_events:` (`client/handler-events.md`).
- `tools/ghidra/scripts/DumpC.java`, `tools/extract/handler_fire.py` and
  `client/symbols/<build>/handler-fire.yaml`: what each handler fires (event, format,
  helper) and which packet read fills each format position; `merge_fire.py` writes it
  into 179 fiches as `client_fire:` and names the three layouts the binary and the UI
  agree on (`0x092B`, `0x0649`, `0x076A`).
- ADR 0008 and `client/lua-packet-api.md`: the client's Lua packet API (`CreatePacket`,
  `RegisterPacket`, `CDataStore` `Put*`/`Get*`/`Send`) is callable from an insecure addon
  and is now the `L5` replay channel; CoaProbe gained `pksend`, `pkwatch`, `pkfind`,
  `pkmeta` (coa-server-guide `df441fd`).
- `tools/replay/manastorm_roundtrip.py`: the Manastorm enter, leave and set-slot pairs
  (`0x0651`/`0x0652`, `0x0665`/`0x0666`, `0x0689`/`0x068A`) proven (`L5`), each with a
  size-check control — the first six fiches at the top of the ladder.
- `0x0749`/`0x074A` draft start/stop: one binding, a computed opcode, empty packets.
- The Lua packet API (`CreatePacket`, `Put*`/`Get*`, `Send`, `RegisterPacket`) documented
  as a candidate replay tool; 33 named CMSGs recorded as having no sender in this build.

### Changed

- `client_sender.py`: `DAT_10bc90cc` is `Put(u32)`, not an opcode-only write; the scan now
  records further calls as `u32` fields and follows the `FUN_1008e4c0` send helper.
  158 of 203 senders recovered (was 150); no earlier layout changed.

- Project foundations: evidence ladder (`docs/EVIDENCE.md`), investigation loop
  (`docs/METHOD.md`), architecture, runbook and roadmap.
- ADR 0001 (evidence ladder), 0002 (YAML fiches and codegen), 0003 (RVA and build identity).
- Fiche schema and its linter (`tools/lint/lint_fiches.py`), wired into CI.
- `client/builds.yaml` with the currently unpinned lab client build.
- First fiche: `SMSG 0x0726` character-advancement known entries, graded `hypothetical`
  — it records the field layout as currently believed, the `L1` provenance that produced
  the shipped bug, and the third-party claims that are not yet reproducible here.
- ADR 0004: data snapshots are an identity axis of their own. `client/datasets.yaml`,
  per-table manifests under `client/datasets/`, the `client_datasets:` fiche field and the
  linter rule that requires it as soon as a field is graded `L2`.
- `tools/extract/dbcinfo.py`: fingerprint a DBC set, compare two sets structurally, and
  separate string-block repacking from real content change column by column.
- Registered `ascension-live-2026-09-17` (our lab client, `L2`) and `cointhrow-2026-09-09`
  (third-party upload, `L1`), with their measured delta.
- ADR 0005: the atlas documents the complement of AzerothCore. `tools/extract/ac_baseline.py`
  generates `protocol/known-baseline.yaml` (1 348 opcodes, 114 DBC tables) and the linter
  refuses a fiche duplicating it.
- ADR 0006: the client corpus is referenced, not vendored. `tools/extract/extract_ui.py`
  and `client/corpus.yaml`.
- `tools/extract/peinfo.py`: PE identity and `--compare` between two builds.
- `tools/extract/lua_enums.py`: 93 enums lifted from the client's Lua into
  `protocol/enums/`, each with its source file and line — including
  `Enum.ResetCreditType` (`AbilityReset 1`, `TalentReset 2`, `AbilityUnlearn 3`,
  `TalentUnlearn 4`).
- Registered four client builds with hashes, `ImageBase` and link timestamps, and the
  stock-versus-CoA-patched `Extensions.dll` delta.
- Ascension's full opcode table, recovered from the opcode-name switch in the stock
  `Extensions.dll` by `tools/extract/opcode_names.py`: 2 517 opcodes, 2 059 named, 458
  answering `unknown`, no disassembler needed. It names a `CHARACTER_ADVANCEMENT_LOADOUT`
  family, `LOCK_ENTRY` / `UNLOCK_ENTRY` and `SMSG_CA_AVAILABLE_CREDITS_UPDATE` that no
  public source covers.

- The client's opcode -> handler map: 532 registrations recovered from the
  `push handler; push opcode; call register` shape by `tools/extract/opcode_handlers.py`.
  It shows the unnamed block `0x071f`-`0x072d` is the Character Advancement service with
  real handlers, that `0x0900` — which `azerothcore-wotlk-coa#4128` sends as
  `SMSG_COA_CONFIG` — has no handler at all on this build, and that `0x064A` has one
  despite our talent documentation calling it unused.
- `tools/extract/lua_bindings.py` and 1 229 recovered Lua API bindings (name →
  implementation RVA), the bridge from what the UI calls to what the binary does.
- Located where the Character Advancement rank actually lives: `GetTalentRankByID`
  (`0x0017b410`) reads a separate container of `0x2c`-byte records with the rank at
  `+0x0c`, reached through a singleton at `0x00a315d0`. `SMSG 0x0726` fills a different
  container entirely and has no reach into it.
- A second of `#4128`'s addresses re-derived independently: `ApplyPendingBuild` at
  `0x001742c0`.
- `SMSG 0x0726`'s handler (`0x00171260`), its record deserializer (`0x00166760`, loop at
  `0x00166899`) and the record's constructor (`0x00150020`) disassembled. The six wire
  fields land at struct `+0x04`, `+0x08`, `+0x0c`, `+0x10`, `+0x18`, `+0x1c`; `+0x11`
  through `+0x17` is written by neither, so nothing the packet carries reaches `+0x14`
  where the rank is read. **This packet cannot transmit ranks**, which explains the
  measurement, and `mod-ascension-compat` has been serialising one into it since `#4027`.
- One of `#4128`'s published addresses re-derived independently: `0x09BC`'s handler at
  RVA `0x002fc6c0`, `0x102FC6C0` at this build's ImageBase.

- `tools/extract/client_sender.py` and `tools/codegen/merge_senders.py`: the client-to-
  server direction at scale. Validated against the twelve senders read by hand, then run
  over every custom `CMSG`: 150 of 203 recovered once the two wrapper helpers are
  modelled (`FUN_100e08b0` sends an empty packet, `FUN_1008d690` opens one) — 53 clean
  layouts, 41 marked `via_helper` (a prefix at best), 56 empty packets. Two opcodes are
  query-service request/response pairs, read from their registration. Both steps are in
  `regenerate.sh`.
- `tools/regenerate.sh`: rebuilds every generated artifact from its sources and fails if
  the repository changed. Its first run caught a non-idempotent merge that stripped one
  blank line per rerun from 69 fiches.
- `client/client-senders.md` and twelve client-to-server fiches: the client's senders
  read through the `CDataStore` pointer table. Nine packets the server parses agree with
  its reader; `0x0523` and `0x09C7` get a client-side layout the server never had.
  `0x0727`'s serializer (`FUN_10166a50`) is the exact mirror of `0x0726`'s deserializer.
- `client/symbols/.../anticheat.md`: what the client's anti-cheat is (an
  `ExtendedAnticheatMgr` detection loop whose only local action is to send
  `CMSG_ANTICHEAT_ALERT`; a keyed HMAC-style integrity check; stock Warden), what it is not
  (`MMgr64.exe` is a table-reading helper, `Ascension.ok` carries no hashes), that the CoA
  client patch already bypasses the integrity check, that the fork's server only logs and
  flood-kicks on alerts, and that none of the 707 active Warden checks overlaps a byte the
  patch changes.
- `tools/extract/server_layout.py` and `client/server-layouts.md`: the `#4027` check run
  against the current server. For each of the 16 packets `mod-ascension-compat` writes,
  the `<<` chain is diffed against the client's read sequence. **No server-side layout bug
  found**; all sixteen verified by hand against the decompiled handler, and every "disagree" the
  diff raised turned out to be an extractor limit — loops, leading strings, GUID width,
  phantom trailing fields — each now written down.
- The `#4027` check extended to Manastorm by resolving its `enum Opcode : uint16_t` and
  the two `SendResult` helpers: **27 server-written packets, 27 verified against the
  decompiled handler, none wrong** — `0x0660`'s six operands, float included, read back
  six for six. Seven generic `WorldPacket packet(opcode, …)` senders remain unattributed
  and are listed as such.
- The linter and the index now descend into nested `repeat` blocks, which `WriteProgress`'s
  list-of-lists needed.
- `0x075F` and `0x0760` attributed through the character-selection `SendResult` helper and
  named; the seven remaining unresolved constructions are copies of incoming packets, not
  sends. The server-written set is closed at **29, all verified**.
- Thirty fiches with **named fields** — every packet the server writes, plus `0x0726`:
  `0x0725`, `0x0673`, `0x06BA`, `0x0769`, `0x0770`, `0x0771`, `0x076F`, `0x075E`, and the
  appearance / vanity set `0x0698`–`0x069D`, `0x06A2`, `0x06F7`, `0x06F8`. Widths from the decompiled handler (`L3`),
  names from the server's own serializer (`L1`).
- `packet_layout.py` now requires the advanced cursor to be stored back to `+0x14` before
  a field counts. It does not remove every phantom — structures with their own `+0x14`
  defeat it — and the stricter packet-register rule was tried and dropped because it lost
  real fields. The limit is documented; the decompiled handler is the arbiter.
- `tools/ghidra/ghidra.sh` and the six headless scripts that produced every
  decompilation-based fact, moved from a scratch directory into the repository. The
  project lives in `build/ghidra/`. Before this the rank findings were not reproducible
  from the repository alone, which broke ADR 0001's own rule.
- Fiches for the 19 opcodes the client handles but does not name, `0x0725` included, and
  a hand-written one for `0x0727`. The stub generator had skipped them.
- `tools/extract/server_usage.py` and `client/server-usage.yaml`: the opcodes
  `mod-ascension-compat` sends or handles, written into 68 fiches as `used_by_server:` by
  `tools/codegen/merge_usage.py`. Those are the priority: a wrong layout there is shipped
  code, not missing knowledge.
- `protocol/INDEX.md`, generated by `tools/codegen/index.py`: every fiche in one table
  with its evidence level, whether the client registers a handler, how many fields the
  layout carries and how many UI files name its event.
- `tools/extract/packet_layout.py`: recovers a packet's field widths and their order from
  the handler's cursor arithmetic, following one level into a deserializer when the
  handler delegates. **346 of 532** handlers yield a sequence, merged into 329 fiches by
  `tools/codegen/merge_layouts.py`. Checked against four layouts known independently —
  `0x0926` comes out as `u8, u32`, exactly as `azerothcore-wotlk-coa#4128` describes it.
  Floats are recovered too, because the client reads them with `movss`: that reproduces
  `#4128`'s `0x09BC` layout field for field across its first nine, gate bytes included.
  Strings are partly recovered too, from the pointer-at-cursor idiom (22 fiches): `0x09BC`
  now reproduces `#4128`'s layout entirely except that one of its two strings is missed.
- `tools/codegen/stub_fiches.py` and **752 stub fiches**, one per custom opcode, built
  from the opcode table, the handler map and the UI corpus. Each carries the name, the
  direction, the handler RVA where the client registers one, and the UI files naming its
  event (117 of them). 45 are flagged `reuses_standard_opcode`: AzerothCore uses that
  number for something else. A stub is never overwritten once someone writes into it.
- **Resolved the rank question.** There are two stores: the talent store
  (`0x20` records, key `+0x04`, rank `+0x08`) that `SMSG 0x0726` fills, and the Wildcard
  store (`0x2c` records, key `+0x00`, rank `+0x0c`) filled by
  `SMSG_WILDCARD_ENTRY_LEARNED` (`0x0621`) — identified because its `push_back`,
  `FUN_10a30260`, is that opcode's registered handler. `GetTalentRankByID` reads the
  Wildcard store first and, outside that game mode, falls back to the talent store keyed
  on `*(catalogue_entry + 0)`, which is not the entry id and never matches. So the server
  stores ranks correctly and the native UI cannot display them on this build.

### Fixed

- **Withdrew** the conclusion that `SMSG 0x0726` cannot carry a rank. It rested on
  `#4128`'s unverified claim that the rank is read at struct `+0x14`. Decompiling the
  normal path shows the advancement service's getter (`0x00152920`) walks a stride-`0x20`
  vector, matches the key at `+0x04` and returns `+0x08` — exactly the field the packet
  carries. The `0x0726` handler calls that same getter with the key straight off the wire,
  so `+0x08` is the rank and `+0x04` the key, settled. The measured `0` narrows to one
  question: `GetTalentRankByID` keys its lookup on the *catalogue entry's own first
  field*, which may not be the entry id.
- `#4128`'s reading of `[+0x10] == 1` and `[+0x14]` in `IsKnownID` is confirmed as code,
  but those are a flag and an **array index** into `[service+0x1a8]` / `[service+0x1b4]`,
  not a rank.

- Retracted a doubt this project raised one commit earlier about the `0x0523` / `0x061A` /
  `0x064A` identities from `azerothcore-wotlk-coa#4030`. All three are exactly right. The
  doubt came from reading a packed name blob whose order is not opcode order; the switch
  settles the numbering.
- ADR 0007: the lab is reused from `coa-server-guide`, and the planned decrypting proxy is
  dropped — we own both ends, so the oracle loop is forge server-side, ask the client.
- `tools/replay/0x0726_flag_gate.py`, the first replay script. Exits 2 (inconclusive)
  until the server-side forge command exists; it refuses to conclude when the client is
  running the CoA compat shim.
- A `ca` command in `CoaProbe` (`coa-server-guide` 58d1dd8) answering from
  `C_CharacterAdvancement`, with a `shim` flag.
- The working hypothesis about `cointhrow-2026-09-09`'s lineage, recorded as `L0` with
  what supports it and what would confirm it.

### Changed

- `ImageBase` of both `Extensions.dll` builds measured at `0x10000000`, so the third-party
  absolute addresses on the `0x0726` fiche now carry their RVA. They stay `L1`: the
  arithmetic is sound, the attribution to a build is not.
