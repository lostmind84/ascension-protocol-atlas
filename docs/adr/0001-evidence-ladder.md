# 0001 — Grade every fact on an evidence ladder

- Status: accepted
- Date: 2026-09-19

## Context

`azerothcore-wotlk-coa#4027` shipped `SMSG 0x0726` with its `marker`, `flag` and
`buildTime` fields written as zero. The layout came from a third-party community archive
and had never been put in front of the Ascension client. The client requires `flag == 1`
before `IsKnownID` answers yes, so the packet was accepted by the wire and ignored by
the game.

Nothing in the process was wrong in isolation. The archive was the best source available;
the author said so; the pull request described its limits. What was missing was a
mechanism that made "read in an archive" and "proven against the client" *structurally
different things* rather than two shades of the same confidence.

Without such a mechanism, the strength of a claim lives in prose, gets summarised away in
review, and is gone entirely by the time someone builds on it six months later.

## Decision

Every fact carries an explicit level from `L0` (conjecture) to `L5` (replayed against a
real client by a committed script), assigned **per field**, and enforced by a linter.

Three freeze rules follow from it:

1. No server code may depend on a fact below `L3`.
2. Anything below `L5` used in production is declared in the pull request.
3. `L5` requires an executable replay script; a failing replay demotes the fact.

`docs/EVIDENCE.md` holds the normative text.

## Options considered

- **Prose caveats in each document.** What we did before. Cheap, and it is exactly what
  failed: caveats do not survive summarisation, and they cannot be checked mechanically.
- **A single "verified / unverified" flag.** Simpler, but it collapses the distinction
  that actually matters — a capture and a replay are both "verified", and only one of
  them tells you what the client *requires*.
- **Per-fiche level only.** Cheaper to maintain, but it hides the real failure mode: a
  packet whose first two fields are solid and whose third is invented reads as solid.
- **The per-field ladder.** Chosen.

## Consequences

- Fiches get more verbose, and writing one takes longer. Accepted deliberately: the cost
  falls on the author, the benefit on every later reader.
- Grading is a judgement call and will sometimes be wrong. Rule 4 ("no traceable
  provenance means `L0`") makes the safe direction the default one.
- Third-party claims sit at `L1` even when their author reports live verification. This
  can read as distrust; `CONTRIBUTING.md` states plainly that it is not, and why.
- Some existing server code depends on facts below `L3`. Rule 1 is therefore a target
  with a migration, tracked as roadmap phase P3, not a gate that blocks today's work.
