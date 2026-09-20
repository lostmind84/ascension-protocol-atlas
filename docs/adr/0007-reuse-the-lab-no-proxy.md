# 0007 — Reuse the CoA lab, and drop the decrypting proxy

- Status: accepted
- Date: 2026-09-19

## Context

P1 was planned as four pieces: a lab client under Wine, a probe addon, a decrypting proxy
between client and worldserver, and a packet injection harness.

Three of those already exist outside this repository, in `coa-server-guide`:

- `scripts/coa-client-lab` runs a reflink copy of the client under Proton and gamescope,
  drives it (`start`, `login`, `chat`, `key`, `screenshot`), and asks it questions
  (`probe`).
- `addons/CoaProbe` answers those questions from inside the client and returns JSON, via
  a SavedVariable flushed on `/reload`.
- `coa-slot` runs the worldserver the client connects to.

Rebuilding any of it here would be duplicated work and a second thing to keep running.

The proxy is a different matter. It was planned to observe traffic, which made sense when
the reference was a live realm nobody controlled. In this lab **we own both ends**: the
worldserver is ours and can log or forge whatever it sends, and the client is ours and can
be asked what it understood. A man-in-the-middle between two endpoints we already control
adds a moving part and answers nothing new.

## Decision

- The atlas does not ship a lab. It uses `coa-client-lab`, `CoaProbe` and `coa-slot`, and
  contributes to them in their own repository when they fall short — as with the `ca`
  probe command, which answers from `C_CharacterAdvancement`.
- **No decrypting proxy.** The oracle loop is: forge the packet on the server, ask the
  client through the probe. Two ends we control, no interception.
- The atlas owns only the replay scripts that drive that loop and assert a fiche's claims.

## A note on how this was nearly got wrong

This ADR first concluded that a forge command had to be written into
`mod-ascension-compat`. That was an assumption, not a finding: nobody had looked. Grepping
the core turned up `.debug send opcode`, which has been in AzerothCore all along and does
exactly the job.

The scope rule of ADR 0005 — document the complement of AzerothCore, never re-do it —
applies to tooling as much as to fiches. Check the core before building.

## Options considered

- **Build a lab inside the atlas.** Self-contained, and a second client copy, a second
  launcher and a second probe to maintain. Refused.
- **Keep the proxy for observation.** Genuinely useful against a realm we do not control.
  There is no such realm any more, and server-side logging covers the rest.
- **Reuse, contribute upstream, own only the replays.** Chosen.

## Consequences

- A replay script depends on tooling in another repository. It checks for it and fails
  with the command to install rather than a stack trace.
- Improvements to the oracle land in `coa-server-guide`, where they also serve the
  existing gameplay and client-check workflows.
- Forging packets needs no new code either. AzerothCore already ships `.debug send opcode`
  (`RBAC_PERM_COMMAND_DEBUG`, `src/server/scripts/Commands/cs_debug.cpp`): it reads
  `opcode.txt` from the worldserver's working directory — `/azerothcore` in the slot
  containers — and sends the packet described there to the commanding player. It takes a
  decimal opcode and `<type> <value>` pairs (`uint8`, `uint16`, `uint32`, `uint64`,
  `float`, `string`, plus GUID and position helpers), which covers every field of
  `0x0726`. The file is delivered with `docker cp`; verified against slot 1.
  **P1 therefore requires no change to `azerothcore-wotlk-coa` at all.**
- If a real Ascension realm is ever found running again, the proxy decision must be
  revisited — this ADR rests on both ends being ours.

## The shim precondition, measured rather than assumed

The CoA client patch ships `Ascension_Collections/CharacterAdvancementCompat.lua` and
`CharacterAdvancementStateCompat.lua`, which set
`ASCENSION_LOCAL_CHARACTER_ADVANCEMENT_COMPAT`. Neither file is in the stock
`patch-B.MPQ`.

The first version of this ADR said a protocol run therefore needs the stock archive.
Grepping both files shows the override is narrower than that. They reassign exactly six
functions:

`GetActiveChrSpec`, `SwitchActiveChrSpec`, `CanSwitchActiveChrSpec`, `GetEntriesByClass`,
`GetEntryByInternalID`, `GetPendingRankByEntryID`.

`IsKnownID`, `GetTalentRankByID`, `IsLockedID`, `IsTalentID` and `IsKnownSpellID` are
**not** among them, so those five answer natively even with the shim loaded. The rule is
therefore per function, not per client: check whether the oracle you are about to use is
one of the six. `CoaProbe`'s `ca` answer carries `shim` so a run can say which client it
was on.

This matters practically, because the stock `patch-B.MPQ` could not reach the lab server
at all: the CoA patch also carries `GlueXML/RealmList/RealmList.lua`, and with the stock
archive in place the client never contacted the authserver. Running on the patched client
was not a shortcut — it was the only way the experiment could run today.
