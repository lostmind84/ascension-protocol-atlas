# 0005 — Document only what AzerothCore does not already implement

- Status: accepted
- Date: 2026-09-19

## Context

AzerothCore already implements the whole standard 3.3.5a protocol: 1 348 opcodes in
`src/server/game/Server/Protocol/Opcodes.h`, the highest being `0x09b2`. It also loads
114 DBC tables through `DBCStores`. All of that is named, maintained and tested by an
active upstream project.

An atlas that re-described any of it would be doing work already done, and would create a
second source of truth that drifts from the core's. The part nobody has written down is
Ascension's own additions — the custom opcodes, the custom tables, the custom UI.

Checked against the core's table, every opcode this project currently cares about —
`0x0523`, `0x061a`, `0x064a`, `0x06e5`, `0x0725`, `0x0726`, `0x0727`, `0x0900`, `0x0926`,
`0x09bc`, `0x09d0` — is absent from it. The custom surface is exactly the gap.

## Decision

The atlas documents the complement of AzerothCore, not the union.

- `tools/extract/ac_baseline.py` reads the core checkout and generates
  `protocol/known-baseline.yaml`: every opcode the core defines, and every DBC table it
  loads.
- The linter refuses a fiche whose opcode is in that baseline, unless the fiche sets
  `reuses_standard_opcode: true` — because Ascension repurposing a standard number is a
  real possibility and a real finding, but it has to be stated rather than implied.
- UI corpora are scoped to Ascension's own archives. Blizzard's stock FrameXML is public
  and out of scope.

## Options considered

- **Document everything for completeness.** A self-contained reference, at the cost of
  duplicating 1 348 opcodes that upstream already maintains, and of being wrong about
  them the moment upstream changes.
- **Document nothing that touches a standard opcode.** Simpler rule, but it would hide a
  genuinely important case: a standard number carrying custom meaning.
- **Complement, with an explicit opt-in for repurposed numbers.** Chosen.

## Consequences

- The baseline is generated from a specific core checkout and goes stale. It is
  regenerated rather than edited, and the path it came from is recorded in the file.
- "Not loaded by AzerothCore" is **not** the same as "added by Ascension": the standard
  client ships many DBC tables no server ever reads. The generated file says so, and the
  DBC side of the baseline is an orientation aid, not a classification.
- A contributor who documents a standard opcode gets a linter error naming the core's
  symbol for it, which is the fastest possible way to learn the scope rule.
