# The investigation loop

**Normative.** An unknown goes from question to specification through these eight steps,
in this order. Skipping step 2 or 3 to reach the lab faster is the most common way to
waste a lab session.

## 0. Frame

State the unexplained behaviour as one falsifiable sentence.

> "The Character Advancement window renders no tree, even though the server sends the
> known entries."

Open the fiche immediately: `status: unknown`, `evidence: L0`. A question that is not
written down is a question that gets re-asked in six months.

## 1. Harvest the client's own source

Cheapest step, and routinely the most productive. The client documents itself:

- **Lua** (`FrameXML`, `SharedXML` in the MPQ set) is readable source, not a binary.
  Enums, constants, UI cost formulas and API names all live there in the clear.
- **DBC** files carry the catalogues.
- **XML** carries the frame hierarchy and event names.

Anything found here is `L2` and authoritative for what it covers. Record it in
`protocol/enums/` so nobody harvests it twice.

## 2. Locate it in the binary

Entry points, in order of yield:

1. **The opcode name-stub table** in `Extensions.dll` — it maps opcode numbers to their
   original names. Highest-value target in the whole binary.
2. **The packet dispatcher** — gives the exhaustive inventory of handled opcodes,
   including ones nobody has named yet. This is how you learn what you do not know.
3. **String references** to Lua API names (`IsKnownID`, `ApplyPendingBuild`) — the bridge
   from step 1's findings into the binary.

Name the functions in Ghidra, export symbols to `client/symbols/<build>/`, commit them.
Findings here are `L3`.

## 3. Propose a layout

Write the fiche's `layout:` with a per-field evidence level. Mark uncertainty where it
actually is. A field you believe is padding is a field you have not tested.

## 4. Build the probe

Climb the ladder; do not start at the top.

- **Level A — Lua probe (in-client addon).** Calls the native API and reports the answer
  over an addon channel message. No binary instrumentation. Answers most questions.
- **Level B — Frida hook.** Attaches to the client, hooks a function by RVA, logs
  arguments, return values and pointed-to memory. For what the Lua layer cannot see.
- **Level C — interactive debugger** (x32dbg, Cheat Engine). Manual, not reproducible.
  Use it to *find*; never to *prove*. Whatever it finds gets re-established at level A or
  B before it counts.

## 5. Experiment

Forge the packet, send it to the client, ask the oracle. Bisect each unknown field:

```
0x0726 with flag=0  ->  IsKnownID(entry) == false
0x0726 with flag=1  ->  IsKnownID(entry) == true
=> flag is a gate; required value 1.
```

Record failures as carefully as successes. A field that changes nothing when you vary it
is information: it is padding, or it is read by something you have not found yet. Say
which one you concluded, and why.

## 6. Freeze

Write the `tools/replay/` script. Run it. Record `last_run` in the fiche. The fact is now
`L5` — meaning someone else can re-establish it without you. The script's channel is the
client's own Lua packet API through CoaProbe (`pkwatch`, `pksend`; ADR 0008,
`client/lua-packet-api.md`) plus `.debug send opcode` for what the server sends;
`tools/replay/manastorm_roundtrip.py` is the model.

## 7. Integrate

Run codegen. Open the pull request on the server repository citing the fiche
(`atlas:0x0726@<commit>`). The pull request does not re-explain the evidence; it points
at it.

## Why the order matters

Steps 1 and 2 are cheap and narrow the search space. Step 5 is expensive and answers one
question at a time. Every hour spent on the corpus and the disassembly saves several at
the lab bench — and going to the bench without a hypothesis produces sessions that end
with "it did not work" and nothing written down.

Conversely: disassembly without a lab produces `L3` that accumulates and never matures.
Both halves are required. That is why P1 (lab) lands before P2 (census) in the roadmap.
