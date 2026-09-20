# Evidence ladder

**Normative.** Every fact in this repository carries a level. Levels are assigned per
*field*, not per opcode — a packet whose first two fields are proven and whose third is
guessed is not a proven packet.

## The levels

| Level | Name | Source | What it is good for |
| --- | --- | --- | --- |
| `L0` | `CONJECTURE` | A working hypothesis. Someone's reasoning. | Nothing. It orients the next experiment. |
| `L1` | `ARCHIVE` | A third-party community source: an archive repository, a forum post, another project's code, someone else's pull request. | Pointing the search. Never a layout. |
| `L2` | `CLIENT-SOURCE` | Read directly from the client's own Lua, XML or DBC. | Names, enums, constants, formulas. Authoritative for what it covers. |
| `L3` | `STATIC` | Derived from disassembling `Extensions.dll`, with the RVA recorded. | Field layouts, sizes, comparisons, control flow. Bounded by analyst error. |
| `L4` | `CAPTURE` | Observed in a packet capture of a real Ascension realm, with the capture's provenance recorded in the fiche. No such capture exists: the realms are gone. | Real values, ordering, timing. |
| `L5` | `PROVEN` | Reproduced against a real client in the lab, by a script committed under `tools/replay/`. | Everything. |

## Freeze rules

1. **No server code may depend on a fact below `L3`.**
2. Any fact below `L5` relied on in production is stated explicitly in the pull request,
   together with the open question it leaves.
3. Every fact at `L5` owns a `replay:` entry pointing at an executable script in this
   repository. No script, no `L5`.
4. A fact with no traceable provenance is `L0`, however convincing it sounds.
5. When a replay script fails, the fact is **demoted** out of `L5` in the same commit
   that records the failure. Knowledge rots; it has to say so.

## Capture is not proof

A capture says *"the real server used to send this."*
A replay says *"the client requires this."*

They are not interchangeable, and confusing them is what produced the `0x0726` bug. A
capture can be incomplete, realm-specific, or taken from a build that is not ours. Use
`L4` to learn what to try; use `L5` to decide what to ship.

## Third-party claims

A claim made in someone else's pull request, issue or repository is **`L1` for us**, even
when that author states they verified it live. We grade our own ability to reproduce, not
theirs. When their evidence is shared and we can re-derive the fact, it moves up. When
their notes are private, the claim stays at `L1` and the fiche records why.

This is not distrust. It is the difference between a specification and a rumour.

## Two identity axes

A fact is true of a *binary build* (ADR 0003) and, when it comes from a catalogue, of a
*data snapshot* (ADR 0004). They move independently: the same `Extensions.dll` serves
several DBC generations, and two snapshots of the same generation disagree about which
entries exist.

A fiche therefore names `client_builds:` always, and `client_datasets:` whenever any of
its fields is graded `L2`. The linter enforces the second.

This is also what makes absence readable. The CoA fork is a reconstruction, so a missing
entry in one catalogue proves nothing. Missing from two independent snapshots is evidence;
missing from one is snapshot noise, and
`client/datasets/deltas/` records how much noise there is.

## Recording a level

In a fiche:

```yaml
evidence: L3                  # the weakest level among the fiche's own fields
layout:
  - { name: entryId, type: u32, evidence: L3 }
  - { name: flag,    type: u8,  evidence: L1, notes: "third-party claim, unreproduced" }
provenance:
  - { level: L1, source: "...", claim: "...", note: "..." }
```

The fiche-level `evidence` is always the **minimum** of its fields. The linter enforces it.
