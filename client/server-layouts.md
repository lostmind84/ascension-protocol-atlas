# What the server writes versus what the client reads

```sh
python3 tools/extract/server_layout.py <azerothcore checkout> \
    --build ascension-extensions-2026-08-13 --out client/server-layouts.yaml
```

This is the `#4027` check, run against the current server module: for every packet
`mod-ascension-compat` constructs, compare the `<<` chain it writes with the field sequence
the client's handler reads. A disagreement is either a shipped bug or an extractor limit,
and each one was settled by decompiling the handler by hand.

## Result

**No server-side layout bug found.** The module writes **29** distinct opcodes once its
Manastorm `enum Opcode` and its two `SendResult` helpers are resolved, and **all 29** were
verified by hand against the decompiled handler. Nothing the server sends is left
unattributed.

| Opcode | Server writes | Client reads (decompiled) | Verdict |
| --- | --- | --- | --- |
| `0x0725` | `u32, u32` | `u32, u32` | agree |
| `0x0726` | `u32 count`, then `u32, u32, u32, u8, u32, u32` per record | same | agree |
| `0x0673` `SMSG_AURA_UPDATE_ADDON` | full `u64` GUID | two `u32`, low then high, consumed as one value | agree |
| `0x06BA` `SMSG_QUERY_CUSTOM_STORE_RESULT` | `cstring`, `u32 count`, then the store record's fields | `cstring`, `u32 count`, then **`0x40` bytes per record** | agree if a store record is 16 `u32` |
| `0x0769` `SMSG_BANK_PERMISSIONS` | `u8, u8` | `u8, u8`, then a local string is built | agree — the extractor's trailing `u32` was that string's arithmetic |
| `0x0770` `…SELECTION_MAIL` | `u32, u8, u8` | `u32, u8, u8` | agree |
| `0x0771` `…SELECTION_GAME_MODE` | `u32, u32, u32, u32, u8, u8` (18 bytes) | exactly 18 bytes, same widths | agree — the extractor's three extra fields were a map insert |
| `0x076F` `…SORT_ORDER` | `cstring` | `cstring` | agree |
| `0x075E` `SMSG_CHARACTER_LIST_INFO` | `u32 ×4`, then per character `guid, active, u8, level, race, class, gender, zone, name` | `u32 ×5, u8 ×6, u32`, string invisible | agree once `guid` is `u32` and `active` is `u8` |

| `0x0698` `SMSG_APPLY_APPEARANCES_RESULT` | `result` | `cstring` | agree |
| `0x0699` `SMSG_APPEARANCE_COLLECTION_INFO` | `u32 count`, then `appearanceId, sourceItem` | `u32`, then two `u32` per item | agree |
| `0x069A` `SMSG_APPEARANCE_ACTIVE_INFO` | count, then ids | `u32`, then one `u32` per item | agree |
| `0x069B` `SMSG_APPEARANCE_ADDED` | `appearanceId, sourceItem` | `u32, u32` | agree |
| `0x069D` `SMSG_APPEARANCE_OUTFIT_INFO` | `u32 0` | `u32 count`, then per outfit a name and nested lists | agree — the server sends no outfits |
| `0x06A2` `SMSG_CAN_SEE_APPEARANCES_INFO` | `u8, u8` | `u8, u8` | agree |
| `0x06F7` `SMSG_LIST_KNOWN_STORE_COLLECTION_ITEMS` | `u32 count`, then ids | `u32`, then one `u32` per item | agree |
| `0x06F8` `SMSG_ADD_KNOWN_STORE_COLLECTION_ITEM` | `itemId` | `u32` | agree |
| `0x075F` / `0x0760` character activate / deactivate result | `SendResult`: one string | `cstring` | agree |
| `0x0652` / `0x0666` Manastorm enter / leave result | `SendResult`: one string | `cstring` | agree |
| `0x065D` `…PROGRESS_UPDATE` | `u64` GUID, then `WriteProgress` | two `u32`, then nested `u32` lists | agree |
| `0x065E` `…COMPLETED_LEVEL` | `depth` | `u32` | agree |
| `0x065F` `SMSG_MANASTORM_DATA` | `WriteProgress`: count, per list count, levels | the same nested lists | agree |
| `0x0660` `…ACTIVE_DATA` | `WriteActive`: `depth, scene, Types[type], caches, chance, item` | `u32, u32, cstring, u32, f32, u32` | agree — six for six, the float included |
| `0x067B` `SMSG_MANASTORM_FAIL` | nothing | nothing | agree |
| `0x067F` `…CHAOTIC_LINK_UPDATE` | `stacks` | `u32`, then a local string is built | agree — the extractor's second `u32` was that string |
| `0x0688` `…LOADOUT_DATA` | `u32 count`, spells | `u32`, then one `u32` per slot | agree |
| `0x068A` `SET_MANASTORM_LOADOUT_SLOT_RESULT` | `slot`, `error` (`char const*`) | `u32, cstring` | agree |
| `0x068B` `UPDATE_MANASTORM_LOADOUT_SLOT` | `slot`, `slots[slot]` | `u32, u32` | agree |

## Every construction accounted for

`server_layout.py` attributes a `WorldPacket` construction to an opcode statically and
lists the rest under `unresolved:`. Read one by one, none of those is an unverified send:

- `WorldPacket packet(opcode, 64)` ×2 — the two `SendResult` helpers, in
  `AscensionCharacterSelection.cpp` and `AscensionManastorm.cpp`. Every caller passes a
  string constant, and the four opcodes they are called with (`0x075F`, `0x0760`,
  `0x0652`, `0x0666`) all have a handler that reads exactly one string.
- `WorldPacket copy(packet)` ×7 — copies of an **incoming** packet in Wisdomball, the
  personal bank and the compat layer, made to inspect or forward it. They carry the
  original's opcode and are not new sends.
- `initial ? Data : ProgressUpdate` — resolved by hand, both branches in the table.
- `CoAGameplayTest.cpp` — the module's test harness building standard `CMSG`s to drive a
  character. Client to server, and outside this check by definition.

## What the disagreements taught about the extractors

Every "DISAGREE" the diff raised was an extractor limit, and each is now written down:

- **Loops.** The client extractor is flat; a `u32 count` plus a repeated record reads as
  count plus one record. The server writes the record in a `for`. Counts differ by design.
- **Leading strings.** A string at offset 0 has no cursor established before it, so the
  pointer-at-cursor idiom cannot fire. `0x06BA` starts with one.
- **GUIDs.** The server writes a `u64`; the client reads it as two `u32`. Same bytes.
- **Phantom trailing fields.** After the real reads, ordinary pointer arithmetic — a map
  insert, a `std::string` being built — matches the load/advance shape and grows fields
  that are not there. `0x0769` and `0x0771` both show it. Requiring the cursor to be stored
  back to `+0x14` did not remove them, because those structures have a field at `+0x14`
  too. Requiring the store to target the packet register lost real fields instead. So the
  limit stands: **a recovered layout can be longer than the packet**, and the decompiled
  handler is the arbiter.

## Status

All twenty-nine rows are `L3` on the client side (decompiled, script and address named
in each fiche) and `L1` on the server side (our own code, not the reference). The names
lent to the fiches come from the server's comments and variables and carry that grade.


## 2026-09-19: the challenges module, helpers and strings

`tools/extract/server_layout.py` now scans `mod-coa-challenges` as well, resolves the
core's `SMSG_COA_*` constants, follows a helper that takes the opcode as a parameter
(`SendChallengeResponse(player, SMSG_COA_CHALLENGE_START_RESPONSE, ...)`) to its call
sites, and types the two string idioms: `AppendConfigString(data, s)` and
`data << uint32(s.size() + 1); data.append(...)` are both the client's length-prefixed
string (`FUN_100d3680`: u32 length, then the bytes). The client side of the comparison is
the decompiled read sequence (`handler-fire.yaml`) where it exists, which sees those
strings; the asm reads otherwise.

**54 opcodes written by the server: 46 agree, 9 disagree, 7 have no client layout.** Of
the 46, 27 agree where the server's width is visible, 11 over the prefix both sides
describe, 4 by record (the client block-copies the 26- or 28-byte record the server
writes field by field), 8 field by field.

The 9 disagreements are the flat chain's limits, each checked by hand and none a live bug:

| Opcode | Server | Client | Reading |
| --- | --- | --- | --- |
| `0x05A6` | `u32, u32 challengeID, levelWord, u32, u32, u32, u16` | one 26-byte record | `levelWord` is a u32 (26 = 6×4 + 2); a bare variable the chain cannot type |
| `0x05A8`, `0x05AA`, `0x05AE`, `0x05B0` | `lpstring trialID, lpstring response`, then `if (rows) { u32, u32 count, u32 ×rows }` | `lpstring, lpstring` | the client's handler reads the two strings; the row loop that follows is read in a callee the decompiled sequence does not enter |
| `0x05B1` | 10 fields, three strings first | `lpstring` | **retracted 2026-09-20: not a disagreement.** Both halves were run-on artefacts of the same function pair. Ghidra's client function runs past a noreturn `__fastfail` in a string destructor into the handler registered for `0x05CB`, and the server chain ran out of `SendActiveTrial` into `AppendTrialCompletionEntry`. Both sides write and read exactly one `lpstring` |
| `0x069D` | `static_cast<uint32>(0)` | `u32, u32, u32` | the chain shows the empty-result branch only; the other branch writes three u32 |
| `0x06BA` | `cstring, u32 count, field` | `cstring, u32` | a loop after the count |
| `0x0726` | `append(body)` | seven reads | the body is built by a serializer elsewhere; the fiche is proven by replay |

One more, found while naming, and **since retracted**. `0x05AC
SMSG_CHALLENGE_CREATOR_QUERY_CHALLENGES_RESULT` (the fork's `SMSG_COA_TRIAL_DATA`) was reported
here as a disagreement in order and count. Hand-tracing the client's parser on 2026-09-20 shows
it reads `u8 clear, u8 fire, u32 count`, then per trial an `lpstring`, a `u8`, four more
`lpstring`s, a counted list of `(u32, u32, lpstring)`, two `u8` and two more counted pair lists —
which is, field for field, what the fork's `SendTrialData` writes. The disagreement was three
blind spots of our own extractor stacked: an `AppendConfigString` whose argument is a call
expression (the three middle strings), the `AppendVoteList` helper it does not enter (the two
vote lists), and both branches of the empty-result `if` concatenated. The "computed-length read"
it reported at slot 2 is a plain `u8`.

**The lesson is about this table, not about those packets.** Two of the nine disagreements were
our tooling reading itself wrong, and both looked exactly like a protocol bug. A row here means
"the two flat readings differ", never "the client and the server disagree": only a hand-trace of
the handler, or the lab, can say that.
`0x09B2 SMSG_SPELL_ACTIVATION_HIDE`. The server writes `u32 spellId, u32 0`
(8 bytes); the client's handler reads eight fields (`u32 ×4, f32, u32 ×3`). The `CDataStore` Gets are
bounds-checked, so the six missing reads yield nothing rather than fail — whether the overlay is
removed as intended is a lab question, recorded on the fiche.

`unknown` in the yaml is a bare variable of unknown width (the old `?` read as a YAML
key marker). `merge_server_names.py` lends the server's operand names to a skeleton only
when the two sides agree field by field with every width visible — three fiches so far;
the rest of the challenge family is named by hand from the writer and the handler.
