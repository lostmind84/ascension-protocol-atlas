# AGENTS.md

Operating manual for whoever works in this repository, human or agent. `README.md` says
what it is; this says how to work in it without breaking its one guarantee: nothing here
claims more than its evidence.

## Commands

```sh
python3 -m pip install --user pyyaml

tools/atlas.py lookup 0x0726 | search TEXT | list --dir s2c --layout unknown | coverage
python3 tools/lint/lint_fiches.py                  # the schema; run after any fiche edit
python3 tools/codegen/coverage.py                  # refresh COVERAGE.md and atlas.json (CI checks them)
python3 tools/codegen/index.py                     # refresh INDEX.md
./tools/regenerate.sh ~/CoaServer/client/ascension-live ~/Projects/azerothcore-wotlk-coa
                                                   # the whole chain; fails unless git is clean afterwards
python3 tools/replay/manastorm_roundtrip.py --slot 1 --pair all --control   # an L5 replay (lab)
```

Ghidra work (`tools/ghidra/ghidra.sh`) and the lab loop (slot, client, CoaProbe, `pkwatch`/
`pksend`) are in `docs/RUNBOOK.md`. Outputs that need Ghidra (`handler-strings.yaml`,
`handler-fire.yaml`) are committed; `regenerate.sh` merges them but does not run Ghidra.

## Answering "what is opcode X?"

1. `tools/atlas.py lookup X`, then open the fiche it names.
2. Read `status`/`evidence` first: `unknown` means a name and, at best, widths; the
   fiche's level is the minimum over its fields.
3. `layout` names `field_N` are placeholders. `client_events` (what Lua receives) and
   `client_fire` (what the handler fires, with its format) are hints for naming them, not
   names — see `client/handler-events.md`.
4. `client_code: none` and `layout_state: unknown` together (in `COVERAGE.md`) mean this
   build has no code behind the name; do not infer a layout from the name.
5. Before relying on a fact in server code, check its level: below `L3`, say so in the PR.

## Adding evidence

- A layout read from the binary: cite the handler or sender RVA and the script that
  produced it (`Decomp.java <VA>`, `client_sender.py`); grade `L3` per field.
- A name from the UI: cite corpus file and line; grade `L2`; add `client_datasets:` when
  the fact comes from a DBC snapshot (the linter enforces it).
- A replay: a script under `tools/replay/` that prints PASS/FAIL/INCONCLUSIVE, a
  `replay:` block with `asserts`, `asserts_measured` and `last_run`, and `status: proven`
  with `evidence: L5` on the fields it proves. A `pksend` proves the server's reader, not
  the client's sender: say which.
- A retraction: keep the wrong claim in `provenance` with a note. History is the point.
- Every change of level goes to `CHANGELOG.md`; every structural decision to `docs/adr/`.

## Rules

- `docs/EVIDENCE.md` is normative. A third-party claim is `L1` here even when its author
  reports live verification.
- Document only what AzerothCore does not (ADR 0005). The linter refuses a fiche for an
  opcode the core already names.
- Addresses are RVAs bound to a build in `client/builds.yaml` (ADR 0003). Corpus and DBC
  facts are bound to `client/corpus.yaml` / `client/datasets.yaml` (ADR 0004, 0006).
- Never commit MPQ, DBC, DLL or EXE. `build/` is where extraction lands; it is ignored.
- Generated files say so in their first line; edit the generator, then regenerate. Hand
  fiches say so too ("Regenerating the atlas leaves this file alone").
- Do not invent: a width that was not read, a name that was not seen, a result that was
  not printed. Say "not established" and move on.
- Documentation is in English. Commits follow Conventional Commits; docs and code in the
  same commit.

## Pitfalls seen so far

- A filtered disassembly listing is not evidence of an empty packet: read the raw
  instructions (twice it hid a helper call).
- `DAT_10bc90cc` is `Put(u32)`, not "the opcode write"; a sender scan that assumed the
  latter lost seventeen senders.
- `GetUInt8` on a Lua `CDataStore` reads past the payload without failing: capture a fixed
  count, never "until it stops".
- Ghidra labels cut long string literals; read the bytes back from memory.
- The slot database gets reseeded; check the lab account and character exist before a
  replay. Set `Warden.Enabled = 0` for debugger or patch work (not needed for the Lua loop,
  but not tested with it on).
