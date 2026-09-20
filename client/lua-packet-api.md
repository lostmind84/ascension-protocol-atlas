# The Lua packet API: the client as its own replay tool

`Extensions.dll` hands raw packets to Lua. Found in the binary (`client/client-senders.md`,
"The Lua packet API"), then established on a lab slot on 2026-09-19 with the CoaProbe
addon — an ordinary, insecure addon.

## What the client exposes

| Name | Where | Binding | Role |
| --- | --- | --- | --- |
| `CreatePacket(opcode)` | global | `FUN_1030f620` | a `CDataStore` userdata with the opcode already written |
| `RegisterPacket(opcode, fn)` | global | `FUN_1030fd10` | `fn(opcode, packet)` for every packet with that opcode, through the registrar the C++ handlers use (`FUN_102c4590`) |
| `ClearPacket` | global | `0x0030f550` | not exercised |
| `Send` | method table `CDataStore` | `0x1030fd90` | `packet:Send()` |
| `PutUInt8/16/32`, `PutInt8/16/32`, `PutFloat`, `PutBool`, `PutString` | `CDataStore` | — | write at the cursor |
| `GetUInt8/16/32`, `GetInt8/16/32`, `GetFloat`, `GetBool`, `GetString`, `GetGUID` | `CDataStore` | — | read at the cursor |

`pkfind` on the lab client answered `CreatePacket: _G, RegisterPacket: _G, ClearPacket: _G,
Send: CDataStore`; `pkmeta` listed the methods above. The stock UI wraps the receiving side
in `SharedXML/Util/OpcodeUtil.lua` behind `issecure()`, but the binding itself does not
check: the probe called all of them from an insecure addon and they worked.

## What was measured

- A forged `0x092B` (`.debug send opcode`, `uint32 11, 22, 33`) reached a `RegisterPacket`
  callback; `GetUInt8` read `0b000000 16000000 21000000` first — the cursor starts at the
  payload, after the opcode.
- `GetUInt8` **has no bounds check**: it kept answering past the 12 bytes with whatever
  memory followed, 4096 times, without failing. A watch therefore reads a fixed count
  (`pkwatch <opcode> [bytes]`), the layout's size when known; a captured record says how
  many bytes were *asked for*, never how long the packet was.
- `CreatePacket(0x0651)` + `PutUInt32(1)` + `Send` reached the server, which answered
  `0x0652` with `ENTER_MANASTORM_TOO_LOW_PLAYER_LEVEL\0`; an 8-byte `0x0651` got no answer.
  `tools/replay/manastorm_roundtrip.py --pair all --control` reproduces this for the enter,
  leave and set-slot pairs (`0x0665`→`0x0666`, `0x0689`→`0x068A` echoing the slot); six
  fiches are `L5`.

## `RegisterPacket` replaces the native handler — for the life of the process

Measured on 2026-09-19 (`L5`), then read in the DLL (`L3`):

- With a `pkwatch` on `0x0726` armed, a forged `0x0726` record never made
  `C_CharacterAdvancement.IsKnownID` answer true and `ASCENSION_KNOWN_ENTRIES_UPDATED`
  never fired, although the watch captured the bytes. `pkunwatch` plus `/reload` did not
  bring the handler back. After a client restart without the watch, the same forge passed
  every check of `tools/replay/0x0726_flag_gate.py`.
- `RegisterPacket` (`FUN_1030fd10`) takes a `luaL_ref` of the function, stores it in a
  Lua-side map keyed by opcode (`FUN_1030f220`, `DAT_10be3ea0`), then calls the DLL's
  `SetMessageHandler` hook (`FUN_102c4590` → `FUN_102c4400`) with the trampoline
  `FUN_1030f410`. For an opcode above `0x55e` the hook does a find-or-insert in the
  handler map (`FUN_100bd860`) and **overwrites the handler slot at `+0xc`**; for a stock
  opcode it goes to the exe's original `SetMessageHandler`, which keeps one handler per
  opcode too.
- The trampoline looks the opcode up in the Lua-side map, pushes the referenced function,
  calls it with `(opcode, CDataStore)` and returns `1`. It never calls the handler it
  displaced.
- `ClearPacket` (`FUN_1030f550`) unlinks the Lua-side record only. The trampoline then
  finds nothing and returns; the native handler is not put back. `ClearMessageHandler`
  (`sub_102c3f80`) zeroes the slot. Nothing re-registers the DLL's own handler: the
  process has to restart.

Consequences for the loop:

- Watch a natively handled `SMSG` only when the raw bytes are the measurement, and know
  that the feature behind it is dead on that client until restart. `manastorm_roundtrip.py`
  does this deliberately for `0x0652`/`0x0666`/`0x068A`.
- To observe that a packet *reached* its native handler, watch the event the handler
  fires (`evwatch`, `handler-fire.yaml`) instead: `ca_vertical.py`'s upload check watches
  `ASCENSION_KNOWN_ENTRIES_UPDATED`.
- `run_all.py` runs the byte-capturing replays last; restart the lab client afterwards
  before any test that needs the shadowed handlers.
- The probe's saved watches (`CoaProbeWatch`) are re-registered on every load, including
  a fresh client start: `pkunwatch` first, then restart.

## What it is good for, and what it is not

Both directions of the ladder's top rung, with no proxy, no binary patch and no server
change beyond the forge command AzerothCore already ships:

- **server → client**: forge with `.debug send opcode`, watch with `pkwatch`, read the
  bytes the handler was given, and ask the UI (`probe ca`, `probe spell`, ...) what
  changed. This proves what the client *received* and did.
- **client → server**: `pksend` a layout and watch the reply. This proves what the
  server's reader *accepts*, not what the client's own sender writes — that stays `L3`
  from the decompiled sender, and the two claims are recorded separately in a fiche.

A replay through this API is not the Manastorm UI clicking "enter": nothing here proves
the client would ever build that packet on its own. It proves the wire contract.

## Commands

```sh
coa-client-lab probe pkfind                  # where the API is on this build
coa-client-lab probe pkmeta                  # the CDataStore methods
coa-client-lab probe pkwatch 1618 48         # log the next 0x0652s, 48 bytes each; survives /reload
coa-client-lab probe pksend 1617 u32:1       # CreatePacket + PutUInt32 + Send
coa-client-lab probe log 5                   # the captured packets, hex
python3 tools/replay/manastorm_roundtrip.py --slot 1 --control
```

The addon and its tests live in `coa-server-guide` (`addons/CoaProbe`, commit `df441fd`);
`RUNBOOK.md` has the slot and client preconditions.
