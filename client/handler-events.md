# From a handler to the Lua it feeds

A server-to-client handler in `Extensions.dll` reads the packet, then hands the result to
the UI as an event with arguments. Two automated passes tie the two ends together so a
skeleton layout (`field_0: u32, field_1: u32, ...`) can be named from what the UI does
with it.

## The two passes

1. **`client_strings`** — `tools/ghidra/scripts/HandlerStrings.java` decompiles each of
   the 532 registered handlers and lists the string literals it references (label names
   Ghidra cuts short are read back from memory). 202 handlers reference at least one;
   the ALL_CAPS ones are, with very few exceptions, the event the handler fires:
   `CHALLENGE_START_RESPONSE`, `RECOVERY_QUERY_RESULT`, `WILDCARD_ENTRY_LEARNED`.
   Written into the fiche by `tools/codegen/merge_strings.py`. Evidence `L3`: it is the
   binary's own text.
2. **`client_events`** — `tools/extract/event_args.py` reads the UI corpus for the
   arguments Lua declares for an event. Ascension's mixins dispatch `OnEvent` to a method
   named after the event, so
   `function ChallengesUI:CHALLENGE_START_RESPONSE(challengeID, level, response)` says
   what the event delivers; the development tools' `EventArgNames` table adds a few more.
   374 events have argument names this way. `tools/codegen/merge_events.py` joins them
   to the fiches through `client_strings`: 101 fiches carry a `client_events` block.
   Evidence `L2`: it is Lua source in the corpus.

3. **`client_fire`** — `tools/ghidra/scripts/DumpC.java` writes every handler's
   decompilation to `build/ghidra/handlers-c/`, and `tools/extract/handler_fire.py` reads
   there what the handler fires: the event, the printf-like format the binary passes
   (`"%u%u%u"`, `"%s%b"`), the helper, and — when the handler calls the formatter
   `FUN_10278c90` itself — which packet read fills each format position. 179 fiches
   carry the block; 56 firings have that read-to-position proof. The wrapper family
   (`FUN_100b9620`, `FUN_100b94b0`, `FUN_100d0a50`, ...) takes the same format but its
   arguments travel through stack slots Ghidra does not name, so those record the format
   only. The same pass records the reads a handler makes inside a counted loop as a
   `repeat` block (the flat asm idiom shows a count and one record), folds a u32 length
   plus a copy of that many bytes into one `lpstring`, and types NUL-scanned strings as
   `cstring`. Evidence `L3`.

## What it is and is not

`client_events` names **the event's arguments as Lua receives them**. The handler built
them from the packet; it did not necessarily forward the fields one to one. `0x0593
SMSG_REQUEST_START_CHALLENGE_RESPONSE` reads `u32, u32, u32, u32, u32, u8` and fires
`CHALLENGE_START_RESPONSE(challengeID, level, response)`: three arguments for six fields.
The names are a strong hint for the first two and the last, and say nothing about the
three in the middle. So:

- a `client_events` block becomes `layout` names by script only when the binary proves
  the position: `merge_fire.py` renames `field_k` to the Lua argument at position i when
  the handler's `client_fire` mapping says read k fills format position i, the read count
  equals the layout's field count, the format has as many specifiers as the event has
  named arguments, and the widths fit the specifiers. Three fiches meet all of that
  (`0x092B`, `0x0649`, `0x076A`); the fiche then says so in a comment and in provenance;
- whoever names a layout reads the handler (`tools/ghidra/ghidra.sh run Decomp.java
  <handler VA>`) next to the event's arguments, and cites both;
- a layout named from the event alone is `L2` for those names and stays `hypothetical`.

Of the 263 distinct event strings the handlers reference, 108 have a mixin method, 56
are only mentioned as a string (registered, dispatched some other way) and 99 never
appear in the corpus — fired by the binary for UI that is not in `patch-B`, or for
nothing. A missing `client_events` block therefore proves nothing about the packet.

## Files

| File | Produced by | Level |
| --- | --- | --- |
| `client/symbols/<build>/handler-strings.yaml` | `HandlerStrings.java` (Ghidra; not run by `regenerate.sh`) | L3 |
| `client/event-args.yaml` | `tools/extract/event_args.py` over the corpus | L2 |
| fiche `client_strings:` | `tools/codegen/merge_strings.py` | L3 |
| fiche `client_events:` | `tools/codegen/merge_events.py` | L2 |
| `build/ghidra/handlers-c/*.c` | `DumpC.java` (Ghidra; not committed) | — |
| `client/symbols/<build>/handler-fire.yaml` | `tools/extract/handler_fire.py` over the C dumps | L3 |
| fiche `client_fire:` and the names it proves | `tools/codegen/merge_fire.py` | L3 (names L2) |
