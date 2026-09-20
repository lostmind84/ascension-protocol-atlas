# 0008 — The client's Lua packet API is the replay channel

Status: accepted, 2026-09-19. Extends ADR 0007 (reuse the lab, no proxy).

## Context

ADR 0007 chose to reuse `coa-client-lab` and the CoaProbe addon and to build no proxy.
The lab then had one channel per direction: `.debug send opcode` to forge a packet the
client receives, and the UI's own actions to make the client send one. Reading what the
client received meant asking the UI; sending a chosen payload meant patching a binary or
driving Ghost.

Reading `Extensions.dll` found `CreatePacket`, `RegisterPacket`, `ClearPacket` and the
`CDataStore` `Put*`/`Get*`/`Send` methods bound to Lua (`client/lua-packet-api.md`). On a
lab slot an insecure addon could call all of them.

## Decision

`L5` replays use the client's own Lua packet API through CoaProbe (`pkwatch`, `pksend`):

- server → client: forge with `.debug send opcode`, capture with `pkwatch`, then ask
  the UI what changed;
- client → server: `pksend` the layout, capture the reply with `pkwatch`.

Ghost stays the tool for a bot that must behave like a player; Frida-style hooks stay off
the roadmap unless a fact cannot be reached this way.

## Consequences

- No proxy, no patch, no server change: the loop runs on any claimed slot with the lab
  client logged in.
- A capture is bounded by the count asked for, because `GetUInt8` reads past the payload
  without failing; the fiche's layout gives the count, and a captured record never claims
  a packet length it did not measure.
- A `pksend` proves the server's reader, not the client's sender. A fiche graded `L5`
  through it says so and keeps the sender's `L3` line separate.
- The addon lives in `coa-server-guide`; a change to it is a commit there, referenced
  from here by hash, never copied.
- `RegisterPacket` replaces the client's own handler for that opcode until the process
  restarts, and `ClearPacket` does not restore it (measured and decompiled 2026-09-19,
  `client/lua-packet-api.md`). A replay that needs the feature behind a packet watches the
  event its handler fires (`evwatch`) rather than the packet; byte captures of natively
  handled packets run last, and the lab client is restarted after them.
