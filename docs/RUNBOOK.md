# Runbook

Operational procedures. **This document describes the real state of the lab, not the
intended one.** Sections marked `NOT BUILT YET` are placeholders with their acceptance
criteria; fill them in when the tooling lands, not before.

## Rebuild everything and prove it reproduces

```sh
tools/regenerate.sh ~/CoaServer/client/ascension-live ~/Projects/azerothcore-wotlk-coa \
    ~/CoaServer/client-dbc/original-2026-09-17
```

Runs every extractor and codegen step in dependency order, lints, and exits non-zero if
`git status` is not clean afterwards. A clean run is the reproducibility claim made
concrete. Hand-written fiches are never touched by any step.

## Validate the fact database

Needs only Python.

```sh
python3 -m pip install --user pyyaml
python3 tools/lint/lint_fiches.py
```

Exit code 0 means every fiche is well-formed and internally consistent. It does **not**
mean the facts are true — only a replay run can say that.

## Regenerate the AzerothCore baseline

```sh
python3 tools/extract/ac_baseline.py ~/Projects/azerothcore-wotlk-coa \
    --out protocol/known-baseline.yaml
```

Re-run after pulling the core. The atlas documents the complement of this file (ADR 0005).

## Extract the client corpus

Needs `smpq` (StormLib CLI) on PATH.

```sh
python3 tools/extract/extract_ui.py --id ascension-ui-patch-b-stock \
    --out build/corpus/ascension-ui-patch-b-stock \
    --manifest client/corpus/ascension-ui-patch-b-stock.manifest.yaml \
    ~/CoaServer/client/ascension-live/Data/patch-B.MPQ.ORIGINAL

python3 tools/extract/lua_enums.py build/corpus/ascension-ui-patch-b-stock \
    --corpus ascension-ui-patch-b-stock --out protocol/enums
```

Extraction lands under `build/`, outside version control (ADR 0006). Archives are applied
in the order given; the tool does not guess the client's load order.

Of the client's archives, only `patch-B.MPQ` carries substantial Ascension UI source.
`enUS/locale-enUS.MPQ` and the `patch-enUS*` archives carry Blizzard's stock FrameXML,
which is out of scope.

## Fingerprint and compare DBC sets

```sh
python3 tools/extract/dbcinfo.py manifest <dbc dir> --id <id> --out client/datasets/<id>.manifest.yaml
python3 tools/extract/dbcinfo.py compare <dir A> <dir B>
python3 tools/extract/dbcinfo.py columns <dir A> <dir B> CharacterAdvancement.dbc
```

## Pin a client build

Every fact is attached to a build.

```sh
python3 tools/extract/peinfo.py <client>/Extensions.dll <client>/Extensions.dll.ORIGINAL
python3 tools/extract/peinfo.py --compare <client>/Extensions.dll.ORIGINAL <client>/Extensions.dll
```

Record the hash, `ImageBase`, section count and link timestamp in `client/builds.yaml`.
Without the `ImageBase`, observed absolute addresses cannot be converted to RVA, and per
ADR 0003 a fiche carrying only absolute addresses can never reach `proven`.

Both registered `Extensions.dll` builds have `ImageBase = 0x10000000`, so an absolute
address converts by subtracting it. `--compare` showed the CoA client patch moves no
code: 30 bytes in ten in-place runs, everything else byte-identical, so RVAs carry between
the stock and patched builds outside those ten sites. See
`client/builds/coa-extensions-rev4-2026-09-14.delta.md`.

## Disassembly, and how fast it actually is

Measured on 2026-09-20, on the maintainer's machine, against the imported `Extensions.dll`
project:

| what | cost |
| --- | --- |
| one `ghidra.sh run`, fixed | 3.5 s |
| each function decompiled | about 30 ms |
| 232 functions, one worker | 28 s |
| 232 functions, `farm 4` | 16 s, including creating the four workspaces |
| reflink copy of the 265 MB project | 0.15 s, and no disk until written |

**A Ghidra project takes an exclusive lock** — a second `run` against the same project dies
in `openProject`, and `-readOnly` does not lift it. For a long time this repository treated
that as "Ghidra must be serialised, so one owner batches every decompilation up front and
hands the files to whoever needs them". The numbers above say that was the wrong conclusion:
the lock is on the *project*, not on the tool, and a project copy is free. Serialising cost
far more in round-trips than the 30 ms it protected.

So a worker takes its own workspace:

```sh
GHIDRA_WORKSPACE=agent3 tools/ghidra/ghidra.sh run DumpC.java in.txt out/   # build/ghidra-agent3
tools/ghidra/ghidra.sh farm 4 addresses.txt out/                            # shard one list over 4
```

`build/ghidra-*` is gitignored and disposable; delete a workspace when its agent is done.

**One caveat, measured.** Scripts that create functions or labels write into their own
workspace, so workspaces drift apart cosmetically: over 232 functions, one file differed
between a farmed and a serial run, and only in an auto-generated symbol name
(`_DAT_10be4138` against `_handler_f_10be4138`). Structure, widths and control flow were
identical. Never quote a Ghidra auto-name as evidence; recreate a workspace from the base
project when you want a byte-identical rerun.

**The real bottleneck is reading, not decompiling.** 30 ms of decompilation produces a
200-line function that costs an analyst minutes and a large slice of an agent's context. The
way to go faster is a better extractor — `tools/helper_trace.py`, `tools/extract/lua_keys.py`
— not more workers.

## Disassembly

Two layers. Most of the atlas was recovered with **no disassembler**: the opcode table,
the handler map, the Lua bindings and the packet layouts all come from byte-pattern scans
in `tools/extract/`, plus `objdump -D -b binary -m i386 -M intel` over the bytes at an RVA
for reading a single function.

For decompilation, Ghidra headless, wrapped:

```sh
tools/ghidra/ghidra.sh import <client>/Extensions.dll.ORIGINAL   # once, ~30 min
tools/ghidra/ghidra.sh run Decomp.java 10152920 1017b410          # decompile by VA
tools/ghidra/ghidra.sh run DecompAt.java 1017ca10                 # same, creating the function if Ghidra missed it
tools/ghidra/ghidra.sh run Callers.java 10a30260                  # who calls this
tools/ghidra/ghidra.sh run Refs.java 10bdf65c                     # who references this address
tools/ghidra/ghidra.sh run HandlerStrings.java build/ghidra/handlers.txt client/symbols/<build>/handler-strings.yaml   # literals per handler, ~3 min
tools/ghidra/ghidra.sh run SenderC.java build/ghidra/missing-senders.txt   # CDataStore calls in a sender's C
tools/ghidra/ghidra.sh run DumpC.java build/ghidra/handlers.txt build/ghidra/handlers-c   # one .c per handler, ~3 min
tools/ghidra/ghidra.sh run FuncAt.java build/ghidra/sender-sites.txt build/ghidra/sender-functions.txt   # sender site -> function entry
python3 tools/extract/handler_fire.py build/ghidra/handlers-c <client>/Extensions.dll.ORIGINAL \
    --build ascension-extensions-2026-08-13 --out client/symbols/ascension-extensions-2026-08-13/handler-fire.yaml
python3 tools/extract/result_tables.py build/ghidra/handlers-c <client>/Extensions.dll.ORIGINAL \
    --build ascension-extensions-2026-08-13 --out client/symbols/ascension-extensions-2026-08-13/result-tables.yaml
python3 tools/extract/patch_tables.py <client>/Extensions.dll.ORIGINAL build/ghidra/handlers-c \
    --build ascension-extensions-2026-08-13 --manifest client/datasets/ascension-live-2026-09-17.manifest.yaml \
    --out client/symbols/ascension-extensions-2026-08-13/patch-tables.yaml
tools/handler_brief.py 0x0580 0x0581          # one screen per handler: layout, fire, Lua args, reads
tools/name_fields.py 0x0580 result listingId  # name a skeleton after reading it
```

`HandlerStrings.java` writes `client/symbols/<build>/handler-strings.yaml` and
`handler_fire.py` (over `DumpC.java`'s output) writes `handler-fire.yaml`; both are
committed: `tools/regenerate.sh` merges them (`merge_strings.py`, `merge_fire.py`) but
does not run Ghidra.
Its input is one line per handler, `<hex VA> <opcode>`, produced from `handlers.yaml`.
Only one headless run can hold the project at a time; a second one waits on the lock.

Arguments are **virtual addresses** (ImageBase + RVA, `0x10000000` for this build), in hex
without the `0x`. `GHIDRA_PROGRAM=Ascension.exe.ORIGINAL` runs the same scripts on the
executable (ImageBase `0x400000`), imported with `analyzeHeadless build/ghidra atlas -import
<client>/Ascension.exe.ORIGINAL -processor x86:LE:32:default` (about 45 min). The project lives in `build/ghidra/`, outside version control; the
scripts in `tools/ghidra/scripts/` are what make a decompilation-based fact reproducible,
so a fiche citing one names the script and the address.

`DecompAt.java` exists because Ghidra's analysis does not define a function at every Lua
binding — they are only reached through a data table. It disassembles and creates one at
the given address before decompiling.

## Replay through the client's Lua packet API

The `L5` loop (ADR 0008, `client/lua-packet-api.md`), on a claimed slot with the lab
client logged in on a character (account with the DEBUG permission):

```sh
coa-client-lab probe pkfind                        # CreatePacket/RegisterPacket/Send present on this build?
coa-client-lab probe pkwatch 0x0652 48             # opcode in decimal or hex; bytes to read per packet
coa-client-lab probe pksend 0x0651 u32:1           # client -> server
printf '2347 uint32 11 uint32 22 uint32 33\n' > opcode.txt && docker cp opcode.txt ac-worldserver:/azerothcore/opcode.txt
coa-client-lab chat ".debug send opcode"           # server -> client
coa-client-lab probe log 5                         # the captured bytes, hex
```

`GetUInt8` reads past the payload without failing: give `pkwatch` the layout's size and
read a capture only up to it. Each probe costs a `/reload` (about 15 s); the watches
survive it, and every `/reload` also makes the client upload its known-entries set, which
the server answers with a fresh `0x0726` about 7 s later.

**`pkwatch` disables the client's own handler for that opcode until the client restarts**
(`client/lua-packet-api.md`): `pkunwatch` and `/reload` do not bring it back, and the saved
watches are re-armed on every start. To see that a packet reached its native handler,
`evwatch` the event it fires (`handler-fire.yaml`) instead. Before a replay that needs a
handler you watched earlier: `pkunwatch <opcode>`, then `coa-client-lab stop`, `start N`,
`login`. The 2026-09-19 runs had `Warden.Enabled = 0` on the slot (the user's rule for
protocol work); nothing here patches the client, but the loop has not been run with
Warden on. A replay script under `tools/replay/` wraps the loop and is what a fiche cites.

```sh
python3 tools/replay/run_all.py --slot 1 --update-fiches   # every replay, docs/lab-runs/<date>.md, last_run lines
```

## Lab client and probe

Both live in `coa-server-guide` and are reused, not rebuilt (ADR 0007).

```sh
coa-slot start N                     # worldserver
coa-client-lab start N               # lab client under Proton, on its own workspace
coa-client-lab login ACCOUNT PASSWORD
coa-client-lab probe ca 31194        # the Character Advancement oracle
```

`probe ca` returns `known`, `rank`, `locked`, `isTalent`, `knownSpell`, `pendingRank`,
the active specialization, the AE/TE investment, and `shim`.

**Check `shim` before concluding anything about the wire.** When it is true the client is
running the CoA compat override and its answers come from Lua, not from the packet. For a
protocol run, put the stock `patch-B.MPQ.ORIGINAL` in the lab client's `Data/` first.

**Turn Warden off on the slot first.** The client's anti-cheat only reports — a debugger
makes it send `CMSG_ANTICHEAT_ALERT`, nothing local — but the fork's server, with
`Warden.Enabled = 1`, logs every alert, kicks above five in ten seconds, and runs 707 stock
memory checks with a 24-hour ban. Set `Warden.Enabled = 0` in the slot's `worldserver.conf`
and restart it before attaching Frida or a debugger, or before any run that changes client
memory. See `client/symbols/ascension-extensions-2026-08-13/anticheat.md`.

Known risk: Frida and Wine do not always cooperate. If level-B probing proves unworkable
under Wine, fall back to a Windows VM and record that decision as an ADR.

## Forge a packet

AzerothCore already does this; no server change is needed.

`.debug send opcode` (`RBAC_PERM_COMMAND_DEBUG`) reads `opcode.txt` from the worldserver's
working directory and sends the described packet to the commanding player. In the slot
containers that directory is `/azerothcore`.

```sh
cat > /tmp/opcode.txt <<'EOF'
1830            # 0x0726, DECIMAL -- the command parses it as a number
uint32 1        # count
uint32 31194    # entryId
uint32 1        # rank
uint32 1        # marker
uint8 1         # flag
uint32 0        # buildTime
uint32 0        # reserved
EOF
docker cp /tmp/opcode.txt ac-worldserver:/azerothcore/opcode.txt
coa-client-lab chat ".debug send opcode"
```

Supported tokens: `uint8`, `uint16`, `uint32`, `uint64`, `float`, `string`, and the GUID
and position helpers (`myguid`, `itsguid`, `mypos`, …). The account must hold
`RBAC_PERM_COMMAND_DEBUG`.

## Replay a fact

```sh
python3 tools/replay/0x0726_flag_gate.py --dry-run   # show what would be sent
python3 tools/replay/0x0726_flag_gate.py             # run it
```

Exit codes: `0` the claim holds, `1` it does not, `2` inconclusive — the run could not
establish anything, and the message says what was missing. A replay that cannot run is
never a pass.

## Run the full lab suite

```sh
python3 tools/replay/run_all.py --slot 1 --update-fiches
```

Runs every `tools/replay/*.py` that takes `--slot`, in name order (the byte-capturing
Manastorm replay last), writes `docs/lab-runs/<date>.md` and rewrites the `last_run`
line of every fiche whose `replay.script` ran. It does not change a fiche's `evidence`:
a failed replay is read, explained and demoted by hand (`docs/lab-runs/2026-09-19.md`
shows one whose failure was the probe's own packet watch, not the packet). Restart the
lab client after the suite.

## Troubleshooting

Nothing recorded yet. Add entries here the first time a problem costs you more than
fifteen minutes — including the symptom, the cause and the fix.
