# Retro-audit: the wire claims `#4027` and `#4128` shipped or argued

Roadmap P3. Every wire-format claim the two pull requests on `azerothcore-wotlk-coa`
made, the fiche that now holds it, and where it stands on the ladder. "Withdrawn" means
the atlas measured the opposite; "confirmed" means re-derived here from the binary or the
lab, independently of the PR.

| Source | Claim | Fiche | Now | Standing |
| --- | --- | --- | --- | --- |
| `#4027` | `0x0725` carries `slot, slotCount` for the active specialization | `0x0725` | `L3` widths, names lent by the server (`L1`), agree | confirmed as a layout; unproven in the lab |
| `#4027` | `0x0726` is `u32 count` then records `entryId, rank, marker, u8, buildTime, reserved` (0x20 bytes) | `0x0726` | record `0x20`, wire `u32,u32,u32,u8,u32,u32` → `+0x04,+0x08,+0x0c,+0x10,+0x18,+0x1c` at `L3`; `entryId` and the `u8` at `L5` | confirmed |
| `#4027` | writing `marker`, `flag` and `buildTime` as zero is harmless | `0x0726` | the `u8` is a LOCK flag (`IsLockedID`); zero = unlocked; presence makes `IsKnownID` true | withdrawn as a bug: the packet was accepted, the entries were known; what stayed empty was the rank display, a client defect (below) |
| `#4027` | `0x0727` uploads the same records back (`u32 count`, `RECORD_SIZE` per record) | `0x0727` | the client's serializer `FUN_10166a50` writes `4, 4, 4, 1, 8` per record from the `0x20`-byte store, `L3`; the server's reader agrees | confirmed |
| `#4128` | `0x0726` requires the `u8` to be `1` before `IsKnownID` answers yes | `0x0726` | measured: `u8 = 0` → known and unlocked; `u8 = 1` → known and locked | withdrawn |
| `#4128` | the rank sits at `+0x14` of the record | `0x0726` | the rank is read from `+0x08`, keyed `+0x04`, by `FUN_10152920`; `+0x14` is inside the hole `+0x11..+0x17` | withdrawn |
| `#4128` | `GetTalentRankByID` answers 0 for a non-Wildcard entry whatever the server sends | `rank-source.md` | consults the Wildcard store first, then a lookup keyed on `*(catalogue_entry + 0)`, not the entry id: always 0 outside Wildcard | confirmed, and located: a client defect, not a server placement error |
| `#4128` | `0x09BC SMSG_REALM_INFO` has nine leading fields (`u32,u32,f32,f32,f32,u32,f32,f32,u32`) | `0x09BC` | the same nine at `L3`, then eight `u8`, two `cstring`, a `u8`; `realmId`, `expansion`, `maintenance`, `auctionCutRate` named from the Lua getters | confirmed and extended |
| `#4128` | handler of `0x09BC` at `0x002fc6c0`, `ApplyPendingBuild` at `0x001742c0` | `handlers.yaml`, `0x0727` | both re-derived from the stock build | confirmed |
| `#4128` | the client-side validator refuses the build before `0x0727` leaves | `0x0727` | `ApplyPendingBuild` is the sender; the refusal path is read but not yet reproduced | open (P4) |
| the core's `ascension-talents.md` | `0x064A` has no handler | `0x064A` | it has one (`0x001dd650`), firing `CHARACTER_ADVANCEMENT_ENTRY_PATCHED` | the core document is wrong; correcting it is a change in the server repository |

## What settles the debt

- The three `#4027` packets have fiches with the binary's layouts; the one that mattered
  (`0x0726`) is measured in the lab and its `L1` history is kept on the fiche.
- Nothing shipped by `#4027` was below `L3` once read; what was wrong was the *belief*
  about the flag, and that belief came from `#4128`, not from the fork's code.
- The two `#4128` claims the atlas withdrew are recorded as withdrawn on the fiche and
  were posted on the PR (comment `issuecomment-5742516406`).

## Still owed

- `CoinThrow`'s notes and capture provenance, and the SHA-256 and ImageBase of the
  install behind `cointhrow-2026-09-09`: a request the user makes; the atlas converts his
  addresses to RVA the moment the ImageBase is known (`client/builds.yaml`).
- The correction of `ascension-talents.md` in the server repository.
