# 0006 — The client corpus is referenced, not vendored

- Status: accepted
- Date: 2026-09-19

## Context

The client's interface source is the cheapest source of `L2` facts, and the investigation
loop starts with it. Reading it means extracting it: 1 233 files and 19 MB from
Ascension's `patch-B.MPQ` alone.

`docs/ROADMAP.md` originally said to extract it "into `client/`", which would have
committed it. That contradicts the repository's own rule against committing
redistributable game assets — the rule exists so the atlas can be published, and Lua
shipped inside an MPQ is no less the game's than a DBC is.

## Decision

Extraction writes outside version control, to `build/corpus/<id>/`. What is committed is:

- `client/corpus.yaml`, registering each corpus with its archives and provenance;
- `client/corpus/<id>.manifest.yaml`, generated, listing every file with its size, hash
  and originating archive;
- the facts lifted out of it — `protocol/enums/*.yaml` and fiche fields — each naming the
  corpus, the source path and the line.

`tools/extract/extract_ui.py` applies archives in the order the operator gives on the
command line, later overriding earlier, and records which archive won for each path. It
does not guess the client's load order.

## Options considered

- **Commit the corpus.** Self-contained and searchable by anyone who clones. Refused: it
  redistributes game content and blocks publication, which is the point of the project.
- **Commit only the files a fiche cites.** Smaller, still redistribution, and it makes
  exploratory grepping impossible — which is most of what the corpus is for.
- **Reference with a manifest, vendor nothing.** Chosen.

## Consequences

- A contributor must extract the corpus locally before they can search it. `RUNBOOK.md`
  carries the command, and it takes under a second per archive.
- A cited fact cannot be re-read from the repository alone. Mitigated by quoting enough
  in the fiche — the enum members, the formula, the line number — that the claim is
  checkable, and by the manifest hash proving which file version was read.
- The manifest pins content by hash, so a corpus that changes under us is detectable.
