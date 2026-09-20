# 0003 — Addresses are stored as RVA, bound to an identified build

- Status: accepted
- Date: 2026-09-19

## Context

Facts about a binary are only true for one build of that binary. Third-party notes about
`Extensions.dll` circulate as absolute addresses of a loaded image — `0x102FC6C0`,
`0x10166899` — which are the preferred-base address plus an offset. They break under
rebasing, under ASLR, and under any client update, and they carry no indication of which
build they came from.

A symbol table that cannot say which binary it describes is not reusable by anyone else,
which defeats the purpose of writing it down.

## Decision

- Addresses are stored as **RVA** (offset from the PE `ImageBase`), never absolute.
- Every build is registered in `client/builds.yaml` with the `Extensions.dll` SHA-256 and
  its `ImageBase`.
- Every fiche declares the builds it applies to, in `client_builds:`.
- An observed absolute address may be recorded verbatim in `address_observed:` as raw
  intake, but a fiche carrying only absolute addresses cannot reach `status: proven`.
  The linter enforces this.

## Options considered

- **Absolute addresses, as the source notes use them.** Zero conversion work, and
  unusable the moment the loader or the build changes.
- **Symbol names only.** Stable to read, but there are no exported names to speak of; the
  names in our symbol tables are ours, assigned during analysis.
- **RVA bound to a hashed build.** Chosen. Converting costs one subtraction and makes
  every address portable and attributable.

## Consequences

- Converting requires knowing the `ImageBase`, so pinning the lab client build is a
  prerequisite for any `proven` binary fact. It is a P0 task for that reason.
- Third-party absolute addresses arrive as intake and need a conversion step before they
  can be graded above `L1`. That friction is deliberate — it is the point at which we
  discover we do not know which build a claim came from.
- Multiple builds can be supported side by side: one fiche, several entries in
  `client_builds`, and a symbol table per build.
