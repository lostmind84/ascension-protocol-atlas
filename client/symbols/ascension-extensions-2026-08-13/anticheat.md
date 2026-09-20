# The client's anti-cheat, and what it means for patching the binary

Read from the stock `Extensions.dll` with the atlas tooling (`ImportRefs.java`,
`Callers.java`, `Decomp.java`), the server fork's own handler, the slot's Warden tables,
and the byte delta of the CoA client patch. Every claim names its source.

## What exists in the client

**1. An `ExtendedAnticheatMgr` with a detection loop.** `FUN_10a3d130` lazily builds the
singleton (`ExtendedAnticheatMgr::vftable`) and then cycles through detection routines —
`FUN_100b70d0`, `FUN_100b5a00`, `FUN_100b7400`, … — eleven of which can call the alert
sender `FUN_100b5570`.

**2. Detection = a report, nothing local.** `FUN_100b70d0` is the whole story for one
detector:

```c
if (IsDebuggerPresent()) {
    FUN_100b5570(3, "Caught by IsDebuggerPresent!");   // stack-built string
}
```

and `FUN_100b5570` builds a `CDataStore`, pushes opcode `0x51F` and the reason
`"AntiDebug"` plus the message, and **sends `CMSG_ANTICHEAT_ALERT`**. No exit, no crash,
no local sanction. `CheckRemoteDebuggerPresent` is reached the same way through
`FUN_100b5c00`.

**3. A keyed integrity check** at `FUN_100e5dd0`: an HMAC-style context is initialised
with a 32-byte key at `singleton(FUN_100e5cd0)+0x120` (in `.data`, not in `.vm_sec`),
updated with the bytes `"OK"`, finalised, and compared in constant time against a 32-byte
input. `FUN_100e5d70` copies 32 bytes of the same singleton's key material. Both have no
static caller — they are reached through a vtable.

**4. `.vm_sec`**: `0x8038` bytes, ~27 % zero, the rest high-entropy. Unexamined; the name
suggests a protected blob, and nothing found so far reads from it.

**5. Stock Warden** (`SMSG/CMSG_WARDEN_DATA`, `0x02E6`/`0x02E7`) — Blizzard's own client
module, driven entirely by the server.

## What is NOT anti-cheat

`MMgr64.exe` / the `MemoryBridge` are a 64-bit **data-reading helper**: its strings are
"CString batch read failed for table {}", "Indexed record batch read", "Projected record
batch read", and it monitors the client PID and exits with it. It reads big client tables
out of process for the 32-bit game. It contains `IsDebuggerPresent` because every MSVC
runtime does.

`Ascension.ok` is a launcher manifest — product and module ids, no file hashes. No local
file-integrity enforcement is visible in it.

## The CoA patch already crosses this line

The CoA client patch (`coa-extensions-rev4-2026-09-14`) modifies exactly the verification
cluster. Of its ten sites in `Extensions.dll`:

| Site | Stock function | What the patch does |
| --- | --- | --- |
| `0x000e3dc0` | `FUN_100e3dc0` | prologue → `jmp .local` |
| `0x000e5d70` | `FUN_100e5d70`, the key-material copy | prologue → `jmp .local` |
| `0x000e5dd0` | **`FUN_100e5dd0`, the HMAC compare** | prologue → `jmp .local` |
| `0x001b0b00` | `FUN_101b0b00`, a feature-bitmask gate | `mov al,1; ret` — always allowed |
| `0x002fc620` | `FUN_102fc620`, returns realm-object `+0x48` | `mov al,1; ret` — always "official realm" |
| four more | conditional jumps | forced |

And in `Ascension.exe`: the realmlist string (`us.logon.worldofwarcraft.com:3724` →
`127.0.0.1`), the manifest (`requireAdministrator` → `asInvoker`), four code sites and an
appended `.local`.

So the question "would the anti-cheat object to a modified binary?" has an empirical
answer: **the binary is already modified, the keyed check is already bypassed, and the
client plays.** A further in-place edit — the `GetTalentRankByID` binding, for instance —
is the same kind of change, at a site nowhere near the detection loop.

## The server side is ours

`WorldSession::HandleAnticheatAlert` (`src/server/game/Handlers/MiscHandler.cpp:100`) is
gated on `Warden.Enabled`, then: log at WARN, insert a `player_anticheat_alert` row, notify
online GMs, and **kick only above five alerts in ten seconds**. No ban. The fork chose to
collect alerts, not to act on them.

## Warden: the one real risk, and it is clear today

`Warden.Enabled = 1` on the slot, with 707 memory and page checks (types 178 and 191, all
against the main module — `str` is empty on every row) and a `BanDuration` of 86 400 s.
A check that lands on a patched byte fails and bans.

Intersecting every check's `[address, address+length)` — read as RVA and as VA — with
every byte the CoA patch changes in `Ascension.exe`, including the appended `.local`:
**no overlap.** The stock checks were written for stock `Wow.exe` regions the patch does
not touch. None names `Extensions.dll`.

That is a property of *these* rows, not a guarantee: a new `warden_checks` import, or a
patch to a region a check covers, changes it. The intersection is one command and should
be rerun whenever either side moves.

## What this means for lab work

Attaching a debugger or Frida makes the client send `CMSG_ANTICHEAT_ALERT("AntiDebug", …)`
to the server — which logs it and, above five in ten seconds, kicks. Nothing happens
client-side. On a lab slot that is noise in the log, and it can be silenced by turning
`Warden.Enabled` off for that slot, which also disables the stock Warden checks. Both are
server-side switches on a server we own.

## Status

`L3` throughout for the client-side reading (decompiled, scripts and addresses named).
The server-side facts are read from the fork's own source and configuration. The Warden
intersection is a measurement against the slot's current tables, dated 2026-09-19.
