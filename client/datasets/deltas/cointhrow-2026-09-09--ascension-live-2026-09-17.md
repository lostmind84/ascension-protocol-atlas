# Delta: `cointhrow-2026-09-09` vs `ascension-live-2026-09-17`

Reproduce with:

```sh
python3 tools/extract/dbcinfo.py compare <cointhrow-set> <ascension-live-set>
python3 tools/extract/dbcinfo.py columns <cointhrow-set> <ascension-live-set> CharacterAdvancement.dbc --top 4
python3 tools/extract/dbcinfo.py columns <cointhrow-set> <ascension-live-set> Spell.dbc --top 6
```

Throughout, **A** is `cointhrow-2026-09-09` and **B** is `ascension-live-2026-09-17`.

## Summary

The two sets are the same client generation carrying near-identical content. Every table
has the same `fieldCount` and `recordSize`; **no schema differs**. 304 of 368 tables are
byte-identical. The apparent size of the remaining difference is mostly an artifact:
string blocks were repacked, so every column holding a string offset changes on nearly
every record while the text it points at is unchanged.

**This means the set carries no new structural information**: nothing about layouts,
field meanings or the protocol. Its value is as a second, independent data point for
dating a snapshot and for calibrating absence (see "Why this matters" below).

## Tables

- A: 368 tables, B: 368 tables, all shared.
- Byte-identical: **304**. Differing: **64**.
- Only naming difference: `LFGDungeonExpansion.dbc` (A) vs `LfgDungeonExpansion.dbc` (B).
  B additionally carries its extraction manifest, which is not a DBC.

## CharacterAdvancement.dbc

| | A | B |
| --- | --- | --- |
| records | 10 234 | 10 255 |
| fields / record size | 179 / 692 | 179 / 692 |
| string block | 228 783 | 231 383 |

- Ids only in A: **4** — `6285`, `7051`, `17567`, `34002`
- Ids only in B: **25** — `11539`, `11604`, `11762`, `16606`, `16607`, `36584`, `36736`, `36760`, …
- Common records differing byte-for-byte: 5 053 of 10 230
- **Columns that never differ: 154 of 173.**

The 5 053 collapse to two columns, both string references:

| Column | Byte | Records | Same text | Different text |
| --- | --- | --- | --- | --- |
| 47 | 188 | 4 909 | 4 889 | **20** |
| 64 | 256 | 3 809 | 3 787 | **22** |
| 65 | 260 | 91 | 88 | **3** |

Column 47 resolves to what reads as the display name, 64 to an icon path, 65 to a
description. So the real content difference is roughly **25 entries whose id was
repurposed**, not five thousand:

- `6486`: "Battle Engravings" (A) / "Mind Over Matter" (B)
- `7614`: "Bulwark of Y'shaarj" (A) / "Malignant Armor" (B)
- `7701`: "Dance In The Starlight" (A) / "Improved Eclipse of Fury" (B)

**Entry 31194** — the example `azerothcore-wotlk-coa#4128` uses for `marker` semantics and
`CoAAutomaticDependencies` — exists in both and differs only in column 47's offset. Its
name is identical. His example holds on our data.

## Spell.dbc

| | A | B |
| --- | --- | --- |
| records | 209 140 | 209 510 |
| fields / record size | 234 / 936 | 234 / 936 |

- Ids only in A: 0. Only in B: **370**.
- Columns that never differ: 110 of 234.
- Same pattern: column 136 differs on 199 713 records, of which **199 631 resolve to
  identical text**. Columns 170, 187 and 153 behave the same way.
- Genuine text changes are small and concentrated: ~1 467 descriptions (col 170), 238
  (col 187), 82 (col 136), 20 (col 153).
- Columns 74 and 80 differ on 839 and 1 966 records and are **not** string references —
  the tool's string resolution produces nonsense there, so those are real numeric
  differences whose meaning is unexamined.

## Other notable tables

| Table | A | B | Note |
| --- | --- | --- | --- |
| `ChrSpecs.dbc` | 101 | 101 | byte-identical |
| `ChrClasses.dbc` | 32 | 32 | one record differs |
| `Talent.dbc` | 2 383 | 2 384 | no string block; 6 common records genuinely differ; id `7048` only in B |
| `CharBaseInfo.dbc` | 208 | 209 | 2-byte records, not keyed by id |
| `Achievement.dbc` | 22 618 | 22 603 | 30 ids only in A, 15 only in B |
| `Achievement_Criteria.dbc` | 33 630 | 33 598 | 32 ids only in A, none only in B |

## Why this matters

1. **Calibration of absence.** The CoA fork is a reconstruction, so its own silence about
   an entry proves nothing. Two independent snapshots change that: an id missing from
   both is solid evidence of absence; missing from one is snapshot noise. The 4 A-only
   and 25 B-only Character Advancement ids are the noise floor.
2. **Dating and build identity.** A data snapshot is an identity axis of its own
   (ADR 0004). A fact read from a catalogue has to name which catalogue.
3. **It raises no protocol question.** Same schema everywhere. Nothing here bears on
   opcodes, wire layouts or `Extensions.dll`.

## Limits

- Column identities (47 = name, 64 = icon, 65 = description) are **inferred from the
  resolved text**, not read from a schema. Treat as `L2`-by-inference.
- `as_string` comparison is meaningless on numeric columns; columns 74 and 80 of
  `Spell.dbc` were left unexamined for that reason.
- The remaining 60 differing tables were not examined column by column.
- A's provenance is unknown, so none of this dates either snapshot in absolute terms.
