# Where the Character Advancement rank comes from — resolved

Ghidra headless decompilation of the stock build, plus one lab measurement. Every address
is an RVA on `ascension-extensions-2026-08-13`.

## Answer

There are **two** rank stores, and `GetTalentRankByID` reads the wrong one first and then
fails on the other.

| Store | Record | Key | Rank | Filled by |
| --- | --- | --- | --- | --- |
| Talent store | `0x20` bytes, in `[service+0x20]..[service+0x24]` | `+0x04` | `+0x08` | **`SMSG 0x0726`** |
| Wildcard store | `0x2c` bytes, in `[singleton+0x198]..[singleton+0x19c]` | `+0x00` | `+0x0c` | **`SMSG_WILDCARD_ENTRY_LEARNED` (`0x0621`)** |

```c
// GetTalentRankByID(entryId), RVA 0x0017b410
found = FUN_10a31bb0(entryId, &value);     // Wildcard store, raw id
if (!found) {
    FUN_10173140(L, catalogue[entryId]);   // fallback -> FUN_10152920(*(entry + 0))
    return 2;
}
push(L, value);
```

Outside Wildcard mode the Wildcard store is empty, so every call takes the fallback — and
the fallback keys the talent store on `*(catalogue_entry + 0)` instead of the entry id.

## The talent store, and the three accessors that work

One vector, one key at `+0x04`, three readers:

| Function | Returns | Drives |
| --- | --- | --- |
| `FUN_10155060` | membership | the `0x0726` handler's "already known?" check |
| `FUN_10152920` | `+0x08` | `GetTalentRankByID`'s fallback |
| `FUN_10155640` | `+0x10` (byte) | `IsLockedID` |

`IsLockedID` passes the **raw entry id**. `GetTalentRankByID`'s fallback does not.

## Proof that the fallback's key is wrong

Both observations come from **one forged record** (`tools/replay/0x0726_flag_gate.py` and
its follow-ups, slot 1, entry `31194`):

1. `u8 = 1` → `IsLockedID` answered **true**. `FUN_10155640` returns true only after
   matching `+0x04 == 31194`, so the record **is** in the vector under that key.
2. `+0x08 = 5` on that same record → `GetTalentRankByID` answered **0**.

The Wildcard store was necessarily empty — `0x0621` was never sent — so step 2 took the
fallback, which walks the very vector step 1 just proved the record is in, on the very
field it is keyed by. It returned `0` anyway.

The only remaining variable is the key. **Therefore `*(catalogue_entry + 0)` is not the
entry id**, and the fallback can never match.

## The Wildcard detour, and the correction to the correction

The `0x2c` container is Ascension's **Wildcard** store, which one revision of this file
said, a later revision retracted as an over-reading, and the handler map now settles:
`FUN_10a30260` — the function that does the `push_back`
(`*(s + 0x19c) += 0x2c` after constructing at the end) — is the registered handler for
opcode `0x0621`, `SMSG_WILDCARD_ENTRY_LEARNED`. Its whole neighbourhood is Wildcard:
`0x061E` unlearn-ability result, `0x0644` roll-abilities result, `0x0646` reset-abilities
result, `0x064C` reroll result, `0x06EE`/`0x06EF` misc data.

The retraction was wrong and the original reading was right. Recorded rather than deleted:
the lesson is that "one consumer does not define a container" was sound reasoning applied
to evidence that had already been superseded by the handler map.

Also corrected along the way: `#4128` describes `IsKnownID` as requiring `[+0x10] == 1`
and a rank at `[+0x14]` that is neither `0` nor `0x2c`. Both offsets are real, in
`FUN_10151480`, but that is a **hash-map node** (FNV-1a over the entry id, sentinel at
`[service+0x234]`), and `[+0x14]` is used as an **array index** into `[service+0x1a8]` and
`[service+0x1b4]`. It is not a rank.

## What this means for the server

`SMSG 0x0726` stores the rank correctly, at `+0x08` of a record keyed `+0x04` — exactly
what `mod-ascension-compat` has serialised since `#4027`. The field was never wrong.

What is unusable is `C_CharacterAdvancement.GetTalentRankByID` outside Wildcard mode, and
the extracted corpus shows the native UI reads ranks through it everywhere:
`FrameXML/SpellListItem.lua:79`, `Util/CharacterAdvancementUtil.lua:71`,
`Util/CharacterAdvancementCostUtil.lua:138`,
`Ascension_CharacterAdvancementSeason9/CharacterAdvancement.lua:932`,
`Templates/CASpellButton.lua` in three places.

So on this build a server **cannot** make the native UI display a talent rank, however
correct its packets are. That is a client defect, and it explains why the CoA compat addon
reconstructs ranks from `IsSpellKnown` rather than asking the client — the shim is not a
stopgap for a missing server feature, it is working around a broken getter.

Two ways out, both for later and neither blocked by anything here:

- patch the binding so the fallback passes the entry id rather than `*(entry + 0)` —
  a small in-place edit of the kind the CoA client patch already makes (ten sites today);
- or drive `0x0621` so the Wildcard store answers, which works without touching the
  binary but hangs the rank display off a game-mode store.

## Status

`L3` for every address and offset — decompiled, reproducible. `L5` for the measurement
that closes it. The identification of the `0x2c` store is `L3` from the handler map.
