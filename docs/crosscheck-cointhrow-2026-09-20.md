# Cross-check against CoinThrow's capture reference, 2026-09-20

**The document itself is not in this repository.** It was written by CoinThrow and sent to the
maintainer privately; it is kept outside the tree, at
`~/CoaServer/reference/cointhrow/cointhrow-opcode-dbc-reference-2026-09-20.md` on the
maintainer's machine. Nothing here quotes more of it than a claim needs, and every claim taken
from it is graded `L1` (`docs/EVIDENCE.md`): we cannot re-derive it, because the capture behind
it is not shared. What follows is our comparison, not a copy of their work.

CoinThrow's reference documents 65 custom opcodes
field by field from a **live client session**, which this atlas has never had: our own
layouts come from decompiling the client, theirs from watching the bytes go by. The two
readings are independent, so where they agree the shape is corroborated from both sides,
and where they disagree one of us is wrong about a real packet.

**Grading.** Their claims stay `L1` for us (`docs/EVIDENCE.md`): the capture is not shared,
so we cannot re-derive them. Agreement does not raise our grade — the grade is about our
ability to re-derive, not about their work. What it does is tell us where to stop looking.

**The part that is worth more than the layouts.** The document names the *addresses* of the
client's own Lua builders (for instance the skill-card builder at `0x1009BC60`, the vanity
item builder at `0x1032F6E0`, the Character Advancement node builder at `0x1016C8B0`). Those
we can decompile ourselves, and the key names come straight out of our binary — `L3`, not
`L1`. Two were reproduced the same day: the skill-card builder yields `CardID, Rank, ItemID,
SpellID, Type, Expansion, Class, Quality, IsWildcard, IsDraftMode, IsStarterCard,
IsCollected, CollectedProgress, CollectedRank, QualityCost, MaxRank`, and the vanity item
builder yields seventeen keys, two more than the document lists. This is the route to naming
the `SMSG_PATCH_*` rows, which is where 187 of our skeleton layouts sit.

**Their addresses reproduce only in part on our build.** Decompiling all 232 addresses the
reference names (`tools/extract/lua_keys.py` over the dumps) yields 22 builders and 234 key
names in `client/symbols/ascension-extensions-2026-08-13/lua-keys.yaml` — including the skill
card and the vanity item, whose lists match theirs. Six others do not: at `0x1016C8B0`, which
they call the Character Advancement node builder with 36 keys, our build has a container
teardown with no string in it, and `0x100DAC40`, `0x10A1A220`, `0x10A1A550`, `0x10A1A970` and
`0x10A1AF90` decompile with no key literal either. Either their addresses come from a
different client build than `ascension-extensions-2026-08-13`, or those builders reach their
key names through a callee we have not followed. Until that is settled, a key list of theirs
that we could not reproduce stays `L1` and is not written into a fiche.

## Opcode by opcode

`agree` = same widths in the same order, whatever the names. `adds` = they describe a packet
we hold at `unknown`. `conflict` = the two readings cannot both be right.

| opcode | our name | our layout | their layout | verdict |
| --- | --- | --- | --- | --- |
| `0x0023` | — (no fiche) | — | (prose) | prose only on their side |
| `0x0520` | CMSG_ANTICHEAT_VERSION | — | `unknown`:uint32, `version`:cstring | adds: we hold no layout |
| `0x055E` | CMSG_EQUIPMENTSET_ITEM_PLACE_IN_BANK | unknown_0:u32 | (prose) | agree (a CMSG slot, not a frame) |
| `0x0578` | SMSG_UPDATE_OBJECT_ADDON | guidLow:u32, guidHigh:u32, unknown_2:u32, unknown_3:u32, unknown_4:u32 | `id`:uint32, `flags`:uint32, `field_08`:uint32, `field_0C`:uint32 | agree (they read the guid as id + flags) |
| `0x058D` | SMSG_UPDATE_CONFIGS | intCount:u32, [×intCount], key:lpstring, value:u32, boolCount:u32, [×boolCount], key:lpstring, value:u8, rateC | (prose) | prose only on their side |
| `0x058E` | SMSG_CREATURE_QUERY_RESPONSE_BULK | count:u32, [×count], response:bytes_variable | `count`:uint32, `creatures`:records × count | agree |
| `0x058F` | SMSG_ITEM_QUERY_RESPONSE_BULK | count:u32, [×count], response:bytes_variable | `count`:uint32, `item`:record | agree |
| `0x0590` | SMSG_QUEST_QUERY_RESPONSE_BULK | count:u32, [×count], response:bytes_variable | `count`:uint32, `quests`:records × count | agree |
| `0x0596` | SMSG_LIST_ACTIVE_CHALLENGES | count:u32, [×count], unknown_0:u32, challengeId:u32, level:u32, unknown_3:u32, unknown_4:u32, unknown_5:u32, u | (prose) | ours is finer |
| `0x05BA` | SMSG_LIST_BROKEN_CHALLENGE_RULES | count:u32, [×count], rule:lpstring | `count`:uint32, `rules`:record[] | agree |
| `0x05F9` | SMSG_UPDATE_KNOWN_RANDOM_ENCHANTS | count:u32, [×count], spellId:u32 | `count`:uint32 | agree |
| `0x05FC` | SMSG_UPDATE_RANDOM_ENCHANT_DATA | unknown_0:u32, unknown_1:u32, unknown_2:u32 | `count`:uint32, `id`:uint32, `value`:uint32 | ours stands: the handler reads three fixed u32 with no loop; their single 12-byte sample cannot tell the two readings apart |
| `0x05FD` | SMSG_UPDATE_RANDOM_ENCHANT_SLOTS | count:u32, [×count], enchant:u32 | `slot_count`:uint32, `slots`:uint32[17] | agree |
| `0x0624` | SMSG_UPDATE_SKILL_CARDS | count:u32, [×count], group:bytes_variable | `count`:uint32, `cards`:struct[20] | agree on the count; their 20 cards give the record a size ours left open |
| `0x0634` | SMSG_BUILD_CREATOR_OWNED_BUILDS | count:u32 | (prose) | ours is finer |
| `0x0648` | SMSG_SKILL_CARD_COLLECTION_LIST | unknown_0:u32, block:bytes_96, count:u32, [×count], entry:bytes_12 | `header`:bytes, `count`:uint32, `entries`:struct[28] | no conflict: our own row here misread their `28 x 12` as a 28-byte entry; it is 28 entries of 12 bytes, and our layout was already byte-exact (4 + 96 + 4 + 28*12 = 440) |
| `0x064F` | SMSG_INITIAL_ITEM_COOLDOWNS | count:u32, [×count], unknown_0:u32, unknown_1:u32, unknown_2:u32, unknown_3:u32, unknown_4:u32 | `count`:uint32 | agree |
| `0x0653` | SMSG_PENDING_SKILL_CARD_LIST | count:u32, [×count], name:cstring, unknown_1:u32, unknown_2:u32 | `count`:uint32 | agree |
| `0x065D` | SMSG_MANASTORM_UPDATE_MAX_COMPLETED_LEVEL | playerGuid:u64, listCount:u32, [×listCount], levelCount:u32, [×levelCount], level:u32 | `player_guid`:uint64, `count`:uint32, `levels`:uint32[8] | agree |
| `0x065F` | SMSG_MANASTORM_DATA | listCount:u32, [×listCount], levelCount:u32, [×levelCount], level:u32 | `count`:uint32, `data`:bytes | agree |
| `0x0660` | SMSG_MANASTORM_ACTIVE_DATA | depth:u32, scene:u32, type:cstring, caches:u32, chance:f32, item:u32 | `unknown_00`:uint64, `difficulty`:cstring, `unknown_0C`:bytes | agree (their u64 is our two u32) |
| `0x0666` | SMSG_LEAVE_MANASTORM_RESULT | result:cstring | `Enter`:`CMSG_ENTER_MANASTORM`, `EnterResult`:`SMSG_ENTER_MANASTORM_RESULT`, `ProgressUpdate`:`SMSG_MANASTORM_ | prose only on their side |
| `0x0672` | SMSG_PLAYER_DATA | unknown_0:u8 | `count`:uint32 | conflict: they see a u32 count, we read a u8 |
| `0x0673` | SMSG_AURA_UPDATE_ADDON | targetGuid:u64 | `unit_guid`:uint64, `index`:int32 | adds: an index after the guid |
| `0x0674` | SMSG_AURA_UPDATE_ALL_ADDON | guidLow:u32, guidHigh:u32, count:u32, [×until_end], unknown_0:u32, unknown_1:u32, unknown_2:u32, spellId:u32 | `unit_guid`:uint64, `auras`:record[], `index`:uint32, `guid`:uint64, `id`:uint32, `amount`:int32, `field_14`:u | closes ours: their record is 28 bytes, byte-exact against six packet sizes |
| `0x0699` | SMSG_APPEARANCE_COLLECTION_INFO | appearanceCount:u32, [×appearanceCount], appearanceId:u32, sourceItem:u32 | `count`:uint32, `appearances`:record[] | agree |
| `0x069A` | SMSG_APPEARANCE_ACTIVE_INFO | count:u32, [×count], appearanceId:u32 | `count`:uint32, `active_appearance_ids`:uint32[69] | agree |
| `0x069D` | SMSG_APPEARANCE_OUTFIT_INFO | outfitCount:u32, [×outfitCount], name:cstring, slotCount:u32 | `count`:uint32, `outfits`:record[count] | agree |
| `0x06AD` | SMSG_MANASTORM_REWARD_VISIBILITY | unknown_0:u32, unknown_1:u32, count:u32, [×count], record:bytes_33 | (prose) | prose only on their side |
| `0x06BD` | SMSG_CUSTOM_STORE_TYPE_LIST | count:u32, [×count], unknown_0:u32, unknown_1:u32, unknown_2:u32, string_0:cstring, string_1:cstring | `count`:uint32, `types`:record[] × count | agree |
| `0x06CA` | SMSG_MENTOR_SPECIALIZATIONS_LIST | unknown_0:u8, count:u32, [×count], specialization:u32 | `count`:uint32, `flag`:uint8 | conflict: they put the count first, we the byte |
| `0x06E5` | SMSG_CHAT_INFRACTION | unknown_0:u32, text:cstring, unknown_2:u32 | `0`:uint32, `""`:cstring, `0`:uint32 | agree |
| `0x06EE` | SMSG_LIST_WILDCARD_MISC_DATA | count:u32, [×count], unknown_0:u32, unknown_1:u32, repurchasableRolls:u32, repurchasableAbilityRolls:u32, repu | `count`:uint32, `rows`:struct[20] | agree (their 20 rows match our per-index arrays) |
| `0x06F0` | SMSG_LIST_WILDCARD_QUICK_ROLLING_CONFIGS | count:u32, [×count], config:bytes_8, flag:u8 | `count`:uint32, `rows`:struct[10] | agree |
| `0x06F7` | SMSG_LIST_KNOWN_STORE_COLLECTION_ITEMS | itemCount:u32, [×itemCount], itemId:u32 | `count`:uint32, `item_ids`:uint32[count] | agree |
| `0x06FF` | CMSG_ITEM_STAT_QUERY | — | `item_id`:uint32, `slot_or_type`:uint32 | adds: we hold no layout |
| `0x0700` | SMSG_ITEM_STAT_QUERY_RESPONSE | — | (prose) | adds: we hold no layout |
| `0x0725` | SMSG_UNNAMED_0725 | slot:u32, slotCount:u32 | `active_slot`:uint32, `slot_count`:uint32 | agree, and they call the first field active_slot |
| `0x0726` | SMSG_CHARACTER_ADVANCEMENT_KNOWN_ENTRIES | count:u32, [×count], entryId:u32, rank:u32, marker:u32, flag:u8, buildTime:u32, reserved:u32 | (prose) | prose only on their side |
| `0x0730` | SMSG_CALLBOARD_CACHE_CONFIG_UPDATE | config:bytes_28 | `count`:uint32, `rows`:record[47] | theirs wins: the handler move-assigns a container out of a parse helper, which reads a count then six u32 per record -- 4 + 47*24 = 1132 exactly, and our 28-byte block fitted nothing |
| `0x0743` | SMSG_INSTANCED_AREAS_LIST | unknown_0:u32, count:u32, [×count], area:bytes_variable | (prose) | ours is finer |
| `0x0746` | SMSG_PLAYER_POLL_LIST | count:u32, [×count], poll:bytes_176 | `count`:uint32, `polls`:poll[] × count | agree |
| `0x074F` | CMSG_DRAFT_HAND_OF_FATE_START | — | (prose) | adds: we hold no layout |
| `0x0753` | SMSG_DRAFT_STATE | unknown_0:u32, unknown_1:u8, unknown_2:u32, unknown_3:u32, unknown_4:u8, unknown_5:u32, flags_6:u8, flags_7:u8 | `state`:bytes | ours is finer |
| `0x075E` | SMSG_CHARACTER_LIST_INFO | maxActive:u32, total:u32, active:u32, inactive:u32, [×characters (until the packet ends)], guid:u32, active:u8 | `max`:uint32, `total`:uint32, `active`:uint32, `inactive`:uint32 | agree |
| `0x0768` | SMSG_HONORABLE_COMBAT_ZONES | count:u32, [×count], zone:bytes_variable | `count`:uint32 | agree |
| `0x076F` | SMSG_CHARACTER_SELECTION_SORT_ORDER | sortOrder:cstring | `order`:cstring | agree |
| `0x0770` | SMSG_CHARACTER_SELECTION_MAIL | listIndex:u32, hasMail:u8, hasStoreMail:u8 | `list_index`:uint32, `has_mail`:uint8, `has_store_mail`:uint8 | agree |
| `0x0771` | SMSG_CHARACTER_SELECTION_GAME_MODE | listIndex:u32, activeGameModes:u32, enabledGameModes:u32, teamId:u32, isMercenary:u8, ruleset:u8 | `list_index`:uint32, `active_modes`:uint32, `enabled_modes`:uint32, `team_id`:uint32, `is_mercenary`:uint8, `r | agree |
| `0x077C` | SMSG_AREA_POI_PAYLOAD | unknown_0:u32, json:cstring | `id`:uint32, `json`:cstring | agree, and they name the leading u32 id |
| `0x077D` | SMSG_MISC_PLAYER_DATA_PAYLOAD | unknown_0:u32, payload:cstring | `unknown`:uint32, `json`:cstring | agree |
| `0x07FC` | — (no fiche) | — | (prose) | prose only on their side |
| `0x0900` | — (no fiche) | — | `count`:uint32, `rows`:record[9] | prose only on their side |
| `0x0905` | SMSG_CUSTOM_ASCENSION_POINTS_UPDATE | — | `flag`:uint8, `kind`:uint8, `value`:uint32 | adds: we hold no layout |
| `0x090B` | SMSG_GAME_MODE_CHANGED | mask:u32 | `mode_mask`:uint32 | agree |
| `0x0926` | SMSG_CA_AVAILABLE_CREDITS_UPDATE | creditType:u8, amount:u32 | `type`:uint8, `value`:uint32 | agree (proven L5 here the same day) |
| `0x094E` | SMSG_KNOWN_ADDON_LIST | count:u32, [×count], name:cstring, flag:u8 | `count`:uint32, `name`:cstring, `flag`:uint8 | agree (read from the DLL here the same day) |
| `0x096E` | SMSG_PATCH_SCALING_STAT_DISTRIBUTION | field_0:bytes_88 | `id`:uint32, `values`:uint32[21] | agree: our bytes_88 is their id + 21 u32 |
| `0x096F` | SMSG_PATCH_SCALING_STAT_VALUES | field_0:bytes_96 | `id`:uint32, `values`:uint32[23] | agree: our bytes_96 is their id + 23 u32 |
| `0x09BB` | SMSG_ACCOUNT_INFO | unknown_0:u32, unknown_1:u32, flag_2:u8, flag_3:u8, count:u32, [×count], entry:bytes_variable | `account_id`:uint32, `0`:uint32, `0`:uint16, `character_count`:uint32, `characters[]`:record × count | agree (their u16 is our two bytes), and they name account_id |
| `0x09BC` | SMSG_REALM_INFO | realmId:u32, expansion:u32, unknown_2:f32, unknown_3:f32, unknown_4:f32, maintenance:u32, auctionCutRate:f32,  | `20`:uint32, `0`:uint32, `1.26`:float, `1.0`:float, `1.0`:float, `0`:uint32, `1.0`:float, `0.0833`:float, `200 | conflict in the flag block: they see one u8 before the two strings, we read eight |
| `0x09BD` | SMSG_GAME_EVENT_INFO | event:bytes_52 | `quest_id`:uint16, `flags`:uint16, `start_time`:uint32, `interval`:int32, `0`:uint32, `window`:uint32, `start_ | both true: the block is 52 bytes and they decode its interior; their own offsets overlap, though (flags u16 at +0x02 and start_time u32 at +0x03 share byte 3) |
| `0x09C1` | SMSG_INSTANCE_INFO | unknown_0:u32 | `value`:uint32 | agree |
| `0x09D0` | SMSG_CHARACTER_CUSTOMIZATION_UNLOCKS | — | `0`:uint32 | conflict: they capture a 4-byte payload, we read none -- their own note says the handler ignores it, so both hold and our layout should say so |
| `0x09D1` | SMSG_PATCH_CHR_CLASSES_ROLES | field_0:u32, field_1:u32, field_2:u32, field_3:u32, field_4:u32, field_5:u32, field_6:u32, field_7:u32, field_ | `class_id`:uint32, `role_row`:uint32[10] | agree: our eleven u32 are their class id + ten role columns |

## What to do with it

**Settled on 2026-09-20.** Of the eight conflicts, four are closed: `0x0730` goes to them (our
extractor had flattened a parse helper's reads), `0x0648` was never a conflict but a misreading
of their table on our side, `0x09BD` holds on both sides at once, and `0x05FC` stands here
because their sample cannot separate the two readings. `0x0672`, `0x06CA` and `0x09D0` were
settled earlier the same way. That leaves `0x09BC`'s flag block, which the lab can answer.

Their document has one internal inconsistency worth sending back: in `0x09BD` the offsets given
for `flags` (u16 at `+0x02`) and `start_time` (u32 at `+0x03`) overlap on byte 3.

1. **Conflicts to settle**, in the order they cost least: `0x0672`, `0x06CA`,
   `0x09D0` and `0x05FC` are one re-read of a handler each; `0x0730`, `0x0648` and `0x09BD`
   need a second look at the record size; `0x09BC`'s flag block is a lab question and the
   lab already answers it (`tools/replay/ca_vertical.py --check realm`), so the forge can be
   re-shaped to their reading and re-run.
2. **`0x0674` is closed by them**: the aura record is 28 bytes — index, caster guid, spell
   id, signed amount and two u32 — and the packet sizes divide exactly. Our decompilation
   saw four u32 on one branch and three on another, which is the same record seen badly.
3. **Follow the builder addresses, do not copy the names.** Every key list they give comes
   from a function in the client we also hold. Decompiling it ourselves is one Ghidra run
   and lands at `L3`; copying the list stays `L1` forever.
4. **The DBC naming route they describe** — `acore_world.*_dbc` schema tables from the
   community repack, column count checked against each client DBC header — is re-derivable
   here: we have the client DBCs and the repack is public. That makes the `SMSG_PATCH_*`
   rows nameable at `L2` instead of the 15-30 hours of per-table work the estimate assumed.
5. **Opcodes they cover that we have no fiche for** at all: `0x0023`, `0x07FC`, `0x0900`.
   The first two they resolve as *not* custom-protocol frames; `0x0900` is a real frame with
   no client handler.
