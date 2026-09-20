# 0002 — Facts live in YAML fiches that generate code

- Status: accepted
- Date: 2026-09-19

## Context

The same protocol fact has to reach several audiences: a human reading documentation, the
server's C++, the Go test harness, a Wireshark dissector. Maintained separately, these
drift — and the drift is silent, because nothing compares them.

That drift is the second half of the `#4027` story: the documentation and the shipped
constants were written from the same belief at the same time, so agreeing with each other
proved nothing about either.

## Decision

One YAML fiche per opcode under `protocol/opcodes/` is the single source of truth.
`tools/codegen/` derives every other artifact from it, including the C++ header that
`mod-ascension-compat` consumes instead of declaring its own opcode constants.

Validation is a Python linter (`tools/lint/lint_fiches.py`), not a separate JSON Schema:
the interesting rules are cross-field and cross-file (a fiche's level is the minimum of
its fields; `proven` requires an existing replay script; a referenced build must exist in
`builds.yaml`), which a schema cannot express. One artifact to maintain, not two.

## Options considered

- **Markdown documents.** Readable, not machine-consumable; codegen and mechanical
  checking are both off the table.
- **A database.** Queryable, but not reviewable in a pull request diff, which is where
  the grading judgement actually gets checked.
- **YAML plus a JSON Schema.** The schema covers shape only; the rules that matter here
  are relational. Keeping both in sync is a second drift problem to solve.
- **YAML plus a linter.** Chosen.

## Consequences

- A documented layout and a shipped layout cannot disagree, and a field still at `L1`
  becomes visible at compile time rather than after a merge.
- `mod-ascension-compat` gains a build-time dependency on generated output. Generated
  headers are committed in the consuming repository so an ordinary build needs no atlas
  checkout.
- The linter is code and can have bugs. It stays small and is itself reviewed.
- YAML permits more expressiveness than the fiche format needs; the linter, not the
  format, is what keeps fiches uniform.
