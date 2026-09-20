# Naming the `SMSG_PATCH_*` rows: which tables have a naming source, and which do not

A `.dbc` file has no header naming its columns: `WDBC`, then four counts. So a patch fiche
can say *how wide* each field is and never *what it is called*. `patch-tables.yaml` binds
104 handlers to the DLL's own custom tables and `client/patch-tables.md` reads that
binding; this reading answers the next question —
**for each patch opcode, does a source of column names exist at all, and where is it?**
It names no field. It says where a later pass should look, and where it should not bother.

**That later pass has since run** (2026-09-20), so read this file as the map it was, not as the
state of the fiches. Where it pointed at a source, the fiches now carry names taken from that
source and graded by it: a column name from AzerothCore's `DBCStructure.h` is `L1` — another
project's reading of the same file — a name from the client's own Lua is `L2`, and a name read
out of our binary is `L3`. Where this map found no source, the fiches now say so explicitly
instead of leaving the question open.

Regenerating the atlas leaves this file alone.

## What was measured

Every number in the table below was read here, in this order.

- **The client DBC header.** `records`, `fields`, `recordSize`, `stringBlockSize` unpacked
  with `struct` from the first 20 bytes of each file in
  `/home/fab/CoaServer/client-dbc/original-2026-09-17` — the `ascension-live-2026-09-17`
  snapshot of `client/datasets.yaml`. All 228 files read carry the magic `WDBC`.
- **The manifest.** `client/datasets/ascension-live-2026-09-17.manifest.yaml`, compared
  field by field against those headers.
- **`patch-tables.yaml`.** `client/symbols/ascension-extensions-2026-08-13/patch-tables.yaml`,
  whose `record_size` and `fields` per opcode were compared against the same headers.
- **A second snapshot.** The same headers re-read from `/home/fab/CoaServer/dbc_clientset`,
  which `client/datasets.yaml` registers as `cointhrow-2026-09-09` — a third-party upload,
  `L1`, *not* the lab client's own extraction.
- **AzerothCore's format strings.** `src/server/shared/DataStores/DBCfmt.h` in the fork:
  each `<Name>fmt[]` is one character per column, so its length is a column count that can
  be compared with the client header, and `DBCStructure.h` names the columns it keeps.

What was **not** measured: no handler was disassembled, no packet was captured, no builder
was re-read in Ghidra, and no column was named. The `lua-keys` and `ui getter` cells below
point at a list of names; they do not claim the list is complete, ordered, or aligned to
the record.

## How a naming source was classified

One bucket per row, first match wins:

1. **`lua-keys <builder>`** — a builder in
   `client/symbols/ascension-extensions-2026-08-13/lua-keys.yaml` whose key names are
   unmistakably this table's domain. The key *strings* are `L3` (literals in the build);
   **the builder-to-table pairing is our inference and is graded `L0`** — the extractor
   binds builders to nothing, and its own header warns that the key→offset pairing is a
   heuristic. Eleven rows.
2. **`ui getter <file:line>`** — a getter in `build/corpus/ascension-ui-patch-b-stock`
   whose returned table has its keys read, or whose return tuple is unpacked into named
   locals. `L2` for the names, `L0` again for "these are the row's columns". Paths are
   relative to `.../ascension-ui-patch-b-stock/Interface/`. Eleven rows.
3. **`core DBCfmt <Name>fmt (k/n named)`** — AzerothCore already loads this table: the
   format string has `n` columns, of which `k` are kept and named in `DBCStructure.h`
   (`x` columns are skipped, not named). Seventy rows. Per ADR 0005 the atlas should not
   restate these; the fiche should point at the core.
4. **`repack schema (L1, unverified)`** — the third-party reference claims an ordered
   column list from the community repack's `acore_world.*_dbc` for this table. **No row
   ends here**: every table it claims a repack schema for is one AzerothCore already names,
   so the cell reads `… + repack (L1)` on top of bucket 3. See "The repack lead" below.
5. **`none found`** — nothing in our sources. The cell carries the reference's own verdict
   when it has one, as an `L1` lead: `ref: stock (wowdev, L1)` means it says the row is a
   stock Wrath table whose layout is published on wowdev.wiki; `ref: partial names (L1)`
   means it offers some names, mostly data-derived.

The `bound by` column says where the table name comes from: `L3 ours` = `patch-tables.yaml`;
`L0 name` = inferred from the opcode's own name, for ten opcodes nothing binds (a file of
that name exists in the snapshot and its header is what is printed, but nothing read here
ties the handler to it); `L1 ref` = only the third-party reference names it.

## The map

| Opcode | `SMSG_PATCH_…` | Client DBC | bound by | fields | record | rows | manifest | Naming source |
| --- | --- | --- | --- | ---: | ---: | ---: | --- | --- |
| `0x0567` | CREATURE | `Creature.dbc` | L3 ours | 23 | 92 | 127343 | ok | none found — ref: partial names (L1) |
| `0x0567` | CREATURE | `DungeonEncounterExtra.dbc` | L3 ours | 4 | 16 | 2069 | ok | none found — ref: partial names (L1) |
| `0x0568` | DUNGEON_ENCOUNTER_EXTRA | `Creature.dbc` | L3 ours | 23 | 92 | 127343 | ok | none found — ref: partial names (L1) |
| `0x0568` | DUNGEON_ENCOUNTER_EXTRA | `DungeonEncounterExtra.dbc` | L3 ours | 4 | 16 | 2069 | ok | none found — ref: partial names (L1) |
| `0x0569` | ITEM_ADDON | `ItemAddon.dbc` | L3 ours | 48 | 192 | 563770 | ok | none found — ref: stock (wowdev, L1) |
| `0x056A` | ITEM_DISPLAY_INFO_COLLECTIONS | `ItemDisplayInfoCollections.dbc` | L1 ref | 8 | 32 | 4704 | ok | none found — ref: partial names (L1) |
| `0x056B` | MYSTIC_ENCHANT | `MysticEnchant.dbc` | L3 ours | 31 | 124 | 7841 | ok | lua-keys `f_1009b2f0` |
| `0x056C` | MYTHIC_AFFIXES | `MythicAffixes.dbc` | L3 ours | 16 | 64 | 13409 | ok | none found — ref: partial names (L1) |
| `0x056D` | MYTHIC_KEYSTONE | `MythicKeystones.dbc` | L3 ours | 3 | 12 | 6801 | ok | none found — ref: partial names (L1) |
| `0x056E` | MYTHIC_PLUS_SCALING | `MythicPlusScaling.dbc` | L3 ours | 8 | 32 | 200 | ok | lua-keys `f_102bc6c0` |
| `0x056F` | QUEST | `Quest.dbc` | L3 ours | 29 | 116 | 18561 | ok | none found — ref: partial names (L1) |
| `0x0570` | SPELL_CHARGES | `SpellCharges.dbc` | L3 ours | 2 | 8 | 415 | ok | none found — ref: partial names (L1) |
| `0x0571` | SPELL_CHARGES_CATEGORY | `SpellChargesCategory.dbc` | L3 ours | 3 | 12 | 109 | ok | none found — ref: partial names (L1) |
| `0x0572` | TIMED_DUNGEON | `TimedDungeons.dbc` | L3 ours | 6 | 24 | 81 | ok | none found — ref: partial names (L1) |
| `0x0573` | VANITY_COLLECTION | `VanityCollection.dbc` | L3 ours | 76 | 308 | 10764 | ok | lua-keys `f_1032f6e0` |
| `0x0574` | SPELL_AFFECT | `SpellAffect.dbc` | L3 ours | 3 | 12 | 36849 | ok | none found — ref: partial names (L1) |
| `0x0579` | LFG_ACTIVITIES | `LFGActivities.dbc` | L3 ours | 23 | 92 | 322 | ok | none found — ref: partial names (L1) |
| `0x057A` | LFG_ACTIVITY_CATEGORIES | `LFGActivityCategories.dbc` | L3 ours | 20 | 80 | 16 | ok | none found — ref: partial names (L1) |
| `0x057B` | LFG_ACTIVITY_GROUP_TYPE | `LFGActivityGroupType.dbc` | L3 ours | 19 | 76 | 5 | ok | none found — ref: partial names (L1) |
| `0x0591` | CHALLENGE | `Challenge.dbc` | L3 ours | 53 | 212 | 297 | ok | ui getter `FrameXML/Ascension_TrackerHeader/Ascension_TrackerHeader.lua:66-68` |
| `0x059F` | ITEM_STAT | `ItemStat.dbc` | L1 ref | 39 | 156 | 1513931 | ok | none found |
| `0x05B2` | CHALLENGE_CONDITION | `ChallengeConditions.dbc` | L3 ours | 10 | 40 | 354 | ok | lua-keys `f_1013c7de` |
| `0x05B3` | CHALLENGE_FEATURED | `ChallengeFeatured.dbc` | L3 ours | 5 | 20 | 54 | ok | none found — ref: partial names (L1) |
| `0x05B4` | CHALLENGE_GROUP_REWARD | `ChallengeGroupRewards.dbc` | L3 ours | 10 | 40 | 144 | ok | none found — ref: partial names (L1) |
| `0x05B5` | CHALLENGE_GROUP | `ChallengeGroups.dbc` | L3 ours | 3 | 12 | 1203 | ok | none found — ref: partial names (L1) |
| `0x05B6` | CHALLENGE_REQUIREMENT | `ChallengeRequirements.dbc` | L3 ours | 9 | 36 | 2047 | ok | lua-keys `f_1013c1a1` |
| `0x05B7` | CHALLENGE_REWARD | `ChallengeRewards.dbc` | L3 ours | 11 | 44 | 21677 | ok | lua-keys `f_1013c3d3` |
| `0x05B8` | CHALLENGE_RULE | `ChallengeRules.dbc` | L3 ours | 5 | 20 | 3646 | ok | lua-keys `f_1013c3d3` |
| `0x05B9` | CHALLENGE_SPELL | `ChallengeSpells.dbc` | L3 ours | 10 | 40 | 7702 | ok | lua-keys `f_1013c60f` |
| `0x05BC` | CHALLENGE_REQUIREMENT_TYPE | `ChallengeRequirementTypes.dbc` | L3 ours | 41 | 164 | 22 | ok | none found — ref: partial names (L1) |
| `0x05BD` | CHALLENGE_RULE_TYPE | `ChallengeRuleTypes.dbc` | L3 ours | 36 | 144 | 127 | ok | none found — ref: partial names (L1) |
| `0x05BE` | CHALLENGE_CONDITION_TYPE | `ChallengeConditionTypes.dbc` | L3 ours | 73 | 292 | 18 | ok | none found — ref: partial names (L1) |
| `0x05F3` | CHR_SPECS | `ChrSpecs.dbc` | L3 ours | 65 | 260 | 101 | ok | ui getter `FrameXML/GameTooltip.lua:259-260` |
| `0x05F4` | SPELL_CUSTOM_ATTR | `SpellCustomAttr.dbc` | L3 ours | 11 | 44 | 58648 | ok | none found — ref: stock (wowdev, L1) |
| `0x05F8` | LOADING_SCREENS | `LoadingScreens.dbc` | L0 name | 4 | 16 | 160 | ok | none found |
| `0x0647` | SKILL_CARD | `SkillCard.dbc` | L3 ours | 12 | 48 | 7776 | ok | lua-keys `f_1009bc60` |
| `0x064A` | CHARACTER_ADVANCEMENT | `CharacterAdvancement.dbc` | L3 ours | 179 | 692 | 10255 | ok | ui getter `FrameXML/GameTooltip.lua:405` |
| `0x0663` | CHALLENGE_MODIFIER | `ChallengeModifiers.dbc` | L3 ours | 8 | 32 | 2 | ok | lua-keys `f_1013c3d3` |
| `0x0664` | CHALLENGE_MODIFIER_TYPE | `ChallengeModifierTypes.dbc` | L3 ours | 37 | 148 | 8 | ok | none found — ref: partial names (L1) |
| `0x066C` | SEALED_CARD_COSTS | `SealedCardCosts.dbc` | L3 ours | 25 | 100 | 101 | ok | none found — ref: partial names (L1) |
| `0x066E` | TOKEN_TYPES | `TokenTypes.dbc` | L3 ours | 57 | 228 | 61 | ok | ui getter `FrameXML/Util/TokenUtil.lua:76` |
| `0x0676` | GLOBAL_STRINGS | `GlobalStrings.dbc` | L3 ours | 20 | 80 | 14357 | ok | none found — ref: partial names (L1) |
| `0x0677` | CHALLENGE_LEVELS | `ChallengeLevels.dbc` | L3 ours | 5 | 20 | 1334 | ok | none found — ref: partial names (L1) |
| `0x0678` | ZONE_STORY | `ZoneStory.dbc` | L3 ours | 5 | 20 | 20 | ok | ui getter `FrameXML/WorldMapFrame.lua:1863` |
| `0x067D` | MANASTORM | `Manastorm.dbc` | L3 ours | 9 | 36 | 1017 | ok | none found — ref: partial names (L1) |
| `0x067E` | MANASTORM_MESSAGES | `ManastormMessages.dbc` | L3 ours | 39 | 156 | 291 | ok | none found — ref: partial names (L1) |
| `0x0680` | ZONE_LIGHT | `ZoneLight.dbc` | L3 ours | 7 | 28 | 24 | ok | none found — ref: stock (wowdev, L1) |
| `0x0681` | ZONE_LIGHT_POINT | `ZoneLightPoint.dbc` | L3 ours | 5 | 20 | 461 | ok | none found — ref: stock (wowdev, L1) |
| `0x0686` | SPELL_ADDON | `SpellAddon.dbc` | L3 ours | 23 | 92 | 5629 | ok | none found — ref: stock (wowdev, L1) |
| `0x068C` | MANASTORM_PLAYER_GROUP_MODIFIERS | `ManastormPlayerGroupModifiers.dbc` | L3 ours | 5 | 20 | 15 | ok | none found — ref: partial names (L1) |
| `0x068D` | MANASTORM_MODIFIERS | `ManastormModifiers.dbc` | L3 ours | 15 | 60 | 32768 | ok | none found — ref: partial names (L1) |
| `0x0691` | APPEARANCE_CATEGORIES | `AppearanceCategories.dbc` | L3 ours | 25 | 104 | 68 | ok | none found — ref: partial names (L1) |
| `0x0691` | APPEARANCE_CATEGORIES | `AppearanceDetails.dbc` | L3 ours | 21 | 84 | 17297 | ok | ui getter `FrameXML/UIParent.lua:1787` |
| `0x0692` | APPEARANCES | `Appearances.dbc` | L3 ours | 17 | 68 | 42903 | ok | ui getter `FrameXML/UIParent.lua:1787` |
| `0x0693` | ITEM_APPEARANCES | `ItemAppearances.dbc` | L3 ours | 3 | 12 | 202932 | ok | none found — ref: partial names (L1) |
| `0x0694` | UI_CAMERA_APPEARANCE_CHR_RACES | `UICameraAppearanceChrRaces.dbc` | L3 ours | 5 | 20 | 240 | ok | none found — ref: partial names (L1) |
| `0x0695` | UI_CAMERA_APPEARANCE_WEAPONS | `UICameraAppearanceWeapons.dbc` | L3 ours | 5 | 20 | 36 | ok | none found — ref: partial names (L1) |
| `0x0696` | UI_CAMERAS | `UICameras.dbc` | L3 ours | 10 | 40 | 271 | ok | none found — ref: partial names (L1) |
| `0x06A4` | TUTORIAL_CATEGORIES | `TutorialCategories.dbc` | L3 ours | 18 | 72 | 3 | ok | none found — ref: partial names (L1) |
| `0x06A5` | TUTORIAL | `Tutorial.dbc` | L3 ours | 92 | 372 | 262 | ok | ui getter `AddOns/Ascension_PathToAscension/PathObjectiveDisplayMixin.lua:39` |
| `0x06A6` | TUTORIAL_OBJECTIVE_TYPES | `TutorialObjectiveTypes.dbc` | L3 ours | 19 | 76 | 2 | ok | none found — ref: partial names (L1) |
| `0x06A7` | TUTORIAL_OBJECTIVES | `TutorialObjectives.dbc` | L3 ours | 24 | 96 | 257 | ok | none found — ref: partial names (L1) |
| `0x06A9` | CHARACTER_ADVANCEMENT_CATEGORIES | `CharacterAdvancementCategories.dbc` | L3 ours | 39 | 156 | 51 | ok | none found — ref: partial names (L1) |
| `0x06A9` | CHARACTER_ADVANCEMENT_CATEGORIES | `CharacterAdvancementClassTypes.dbc` | L3 ours | 23 | 92 | 46 | ok | none found — ref: partial names (L1) |
| `0x06AC` | TUTORIAL_KEYWORDS | `TutorialKeywords.dbc` | L3 ours | 64 | 260 | 483 | ok | none found — ref: partial names (L1) |
| `0x06B2` | TUTORIAL_REWARDS | `TutorialRewards.dbc` | L3 ours | 4 | 16 | 591 | ok | none found — ref: partial names (L1) |
| `0x06BE` | SUPER_TRACK | `SuperTrack.dbc` | L3 ours | 8 | 32 | 9763 | ok | none found — ref: partial names (L1) |
| `0x06BF` | QUEST_SUPER_TRACK | `QuestSuperTrack.dbc` | L3 ours | 102 | 408 | 11269 | ok | none found — ref: partial names (L1) |
| `0x06C0` | SPELL_TAG_TYPES | `SpellTagTypes.dbc` | L3 ours | 61 | 244 | 200 | ok | ui getter `FrameXML/Util/CharacterAdvancementUtil.lua:662` |
| `0x06C1` | SPELL_TAGS | `SpellTags.dbc` | L3 ours | 3 | 12 | 488662 | ok | none found — ref: partial names (L1) |
| `0x06C5` | MENTOR_SPECIALIZATIONS | `MentorSpecializations.dbc` | L3 ours | 19 | 76 | 10 | ok | none found — ref: partial names (L1) |
| `0x06CE` | SPELL_SPELL_SUGGESTIONS | `SpellSpellSuggestions.dbc` | L3 ours | 4 | 16 | 353193 | ok | none found — ref: partial names (L1) |
| `0x06D2` | SPELL_STAT_SUGGESTIONS | `SpellStatSuggestions.dbc` | L3 ours | 4 | 16 | 1121 | ok | none found — ref: partial names (L1) |
| `0x06D4` | CHARACTER_CREATION_ARCHETYPE_ROLES | `CharacterCreationArchetypeRoles.dbc` | L3 ours | 71 | 284 | 3 | ok | none found — ref: partial names (L1) |
| `0x06D5` | CHARACTER_CREATION_ARCHETYPE_CATEGORIES | `CharacterCreationArchetypeCategories.dbc` | L3 ours | 73 | 292 | 9 | ok | none found — ref: partial names (L1) |
| `0x06D6` | CHARACTER_CREATION_ARCHETYPES | `CharacterCreationArchetypes.dbc` | L3 ours | 157 | 628 | 56 | ok | none found — ref: partial names (L1) |
| `0x06D7` | CHARACTER_CREATION_PET_DETAILS | `CharacterCreationPetDetails.dbc` | L3 ours | 12 | 48 | 170 | ok | none found — ref: partial names (L1) |
| `0x06D8` | CHARACTER_CREATION_SHAPESHIFT_DETAILS | `CharacterCreationShapeshiftDetails.dbc` | L3 ours | 21 | 84 | 100 | ok | none found — ref: partial names (L1) |
| `0x06D9` | COLLECTOR_CACHE_TYPES | `CollectorCacheTypes.dbc` | L3 ours | 38 | 152 | 1 | ok | none found — ref: partial names (L1) |
| `0x06DA` | COLLECTOR_CACHE_RARITY_TYPES | `CollectorCacheRarityTypes.dbc` | L3 ours | 19 | 76 | 8 | ok | none found — ref: partial names (L1) |
| `0x06DB` | COLLECTOR_CACHE_RARITY_RATES | `CollectorCacheRarityRates.dbc` | L3 ours | 4 | 16 | 351 | ok | none found — ref: partial names (L1) |
| `0x06DC` | COLLECTOR_CACHE_ITEMS | `CollectorCacheItems.dbc` | L3 ours | 26 | 104 | 14 | ok | none found — ref: partial names (L1) |
| `0x06E3` | CHARACTER_CREATION_ARCHETYPE_DETAILS | `CharacterCreationArchetypeDetails.dbc` | L3 ours | 28 | 112 | 1120 | ok | ui getter `GlueXML/CharacterCreateArchetypes.lua:386` |
| `0x06EC` | ITEM_SET_APPEARANCES | `ItemSetAppearances.dbc` | L3 ours | 3 | 12 | 1603 | ok | none found — ref: partial names (L1) |
| `0x06ED` | APPEARANCE_DETAILS | `AppearanceCategories.dbc` | L3 ours | 25 | 104 | 68 | ok | none found — ref: partial names (L1) |
| `0x06ED` | APPEARANCE_DETAILS | `AppearanceDetails.dbc` | L3 ours | 21 | 84 | 17297 | ok | ui getter `FrameXML/UIParent.lua:1787` |
| `0x06F5` | SCREEN_LOCATIONS | `ScreenLocations.dbc` | L3 ours | 2 | 8 | 12 | ok | none found — ref: partial names (L1) |
| `0x06F6` | SPELL_ACTIVATION_OVERLAYS | `SpellActivationOverlays.dbc` | L3 ours | 14 | 56 | 1405 | ok | none found — ref: stock (wowdev, L1) |
| `0x06FA` | OBJECT_SPAWN_VISIBILITY_SETTINGS | `ObjectSpawnVisibilitySettings.dbc` | L3 ours | 7 | 28 | 0 | ok | none found — ref: partial names (L1) |
| `0x06FB` | GAMEOBJECT_DISPLAY_INFO_ADDON | `GameObjectDisplayInfoAddon.dbc` | L3 ours | 2 | 8 | 106834 | ok | none found — ref: partial names (L1) |
| `0x06FC` | CREATURE_DISPLAY_INFO_GEOSET_DATA | `CreatureDisplayInfoGeosetData.dbc` | L3 ours | 4 | 16 | 18935 | ok | none found — ref: partial names (L1) |
| `0x092A` | SPELL | `Spell.dbc` | L1 ref | 234 | 936 | 209510 | ok | core DBCfmt `SpellEntryfmt` (187/234 named) + repack (L1) |
| `0x092C` | SPELL_VISUAL | `SpellVisual.dbc` | L1 ref | 32 | 128 | 23148 | ok | core DBCfmt `SpellVisualfmt` (3/32 named) + repack (L1) |
| `0x092D` | SPELL_VISUAL_KIT | `SpellVisualKit.dbc` | L1 ref | 38 | 152 | 29584 | ok | none found — ref: stock (wowdev, L1) |
| `0x092E` | SPELL_VISUAL_KIT_MODEL_ATTACH | `SpellVisualKitModelAttach.dbc` | L1 ref | 10 | 40 | 7904 | ok | none found — ref: stock (wowdev, L1) |
| `0x092F` | SPELL_VISUAL_EFFECT_NAME | `SpellVisualEffectName.dbc` | L1 ref | 7 | 28 | 18742 | ok | none found — ref: stock (wowdev, L1) |
| `0x0930` | SPELL_MISSILE | `SpellMissile.dbc` | L1 ref | 15 | 60 | 170 | ok | none found — ref: stock (wowdev, L1) |
| `0x0931` | SPELL_MISSILE_MOTION | `SpellMissileMotion.dbc` | L1 ref | 5 | 20 | 1786 | ok | none found — ref: stock (wowdev, L1) |
| `0x0932` | ITEM | `Item.dbc` | L1 ref | 8 | 32 | 563770 | ok | core DBCfmt `Itemfmt` (8/8 named) + repack (L1) |
| `0x0933` | SKILL_LINE | `SkillLine.dbc` | L1 ref | 56 | 224 | 872 | ok | core DBCfmt `SkillLinefmt` (20/56 named) + repack (L1) |
| `0x0934` | SKILL_LINE_ABILITY | `SkillLineAbility.dbc` | L1 ref | 14 | 56 | 40999 | ok | core DBCfmt `SkillLineAbilityfmt` (10/14 named) + repack (L1) |
| `0x0935` | SPELL_ITEM_ENCHANTMENT | `SpellItemEnchantment.dbc` | L1 ref | 38 | 152 | 18035 | ok | core DBCfmt `SpellItemEnchantmentfmt` (34/38 named) + repack (L1) |
| `0x0936` | ACHIEVEMENT | `Achievement.dbc` | L1 ref | 62 | 248 | 22603 | ok | core DBCfmt `Achievementfmt` (24/62 named) + repack (L1) |
| `0x0937` | ACHIEVEMENT_CRITERIA | `Achievement_Criteria.dbc` | L1 ref | 31 | 124 | 33598 | ok | core DBCfmt `AchievementCriteriafmt` (13/31 named) + repack (L1) |
| `0x0938` | ACHIEVEMENT_CATEGORY | `Achievement_Category.dbc` | L1 ref | 20 | 80 | 245 | ok | core DBCfmt `AchievementCategoryfmt` (2/20 named) + repack (L1) |
| `0x0939` | AREA_TABLE | `AreaTable.dbc` | L1 ref | 36 | 144 | 2849 | ok | core DBCfmt `AreaTableEntryfmt` (27/36 named) + repack (L1) |
| `0x093A` | CHAR_START_OUTFIT | `CharStartOutfit.dbc` | L1 ref | 77 | 296 | 981 | ok | core DBCfmt `CharStartOutfitEntryfmt` (29/77 named) + repack (L1) |
| `0x093B` | CHR_CLASSES | `ChrClasses.dbc` | L1 ref | 60 | 240 | 32 | ok | core DBCfmt `ChrClassesEntryfmt` (21/60 named) + repack (L1) |
| `0x093C` | CREATURE_FAMILY | `CreatureFamily.dbc` | L1 ref | 28 | 112 | 399 | ok | core DBCfmt `CreatureFamilyfmt` (25/28 named) + repack (L1) |
| `0x093D` | CREATURE_TYPE | `CreatureType.dbc` | L1 ref | 19 | 76 | 17 | ok | core DBCfmt `CreatureTypefmt` (1/19 named) + repack (L1) |
| `0x093E` | CURRENCY_CATEGORY | `CurrencyCategory.dbc` | L1 ref | 19 | 76 | 14 | ok | none found — ref: stock (wowdev, L1) |
| `0x093F` | CURRENCY_TYPES | `CurrencyTypes.dbc` | L1 ref | 4 | 16 | 69 | ok | core DBCfmt `CurrencyTypesfmt` (2/4 named) + repack (L1) |
| `0x0940` | DUNGEON_ENCOUNTER | `DungeonEncounter.dbc` | L1 ref | 23 | 92 | 2080 | ok | core DBCfmt `DungeonEncounterfmt` (20/23 named) + repack (L1) |
| `0x0941` | FACTION | `Faction.dbc` | L1 ref | 57 | 228 | 417 | ok | core DBCfmt `FactionEntryfmt` (38/57 named) + repack (L1) |
| `0x0942` | FACTION_TEMPLATE | `FactionTemplate.dbc` | L1 ref | 14 | 56 | 871 | ok | core DBCfmt `FactionTemplateEntryfmt` (14/14 named) + repack (L1) |
| `0x0943` | HOLIDAYS | `Holidays.dbc` | L1 ref | 55 | 220 | 58 | ok | core DBCfmt `Holidaysfmt` (52/55 named) + repack (L1) |
| `0x0944` | ITEM_EXTENDED_COST | `ItemExtendedCost.dbc` | L1 ref | 16 | 64 | 13777 | ok | core DBCfmt `ItemExtendedCostEntryfmt` (15/16 named) + repack (L1) |
| `0x0945` | LFG_DUNGEONS | `LFGDungeons.dbc` | L1 ref | 49 | 196 | 430 | ok | core DBCfmt `LFGDungeonEntryfmt` (28/49 named) + repack (L1) |
| `0x0946` | LOCK | `Lock.dbc` | L1 ref | 33 | 132 | 453 | ok | core DBCfmt `LockEntryfmt` (25/33 named) + repack (L1) |
| `0x0947` | PVP_DIFFICULTY | `PvpDifficulty.dbc` | L1 ref | 6 | 24 | 658 | ok | core DBCfmt `PvPDifficultyfmt` (6/6 named) + repack (L1) |
| `0x0948` | SKILL_RACE_CLASS_INFO | `SkillRaceClassInfo.dbc` | L1 ref | 8 | 32 | 230 | ok | core DBCfmt `SkillRaceClassInfofmt` (6/8 named) + repack (L1) |
| `0x0949` | SPELL_SHAPESHIFT_FORM | `SpellShapeshiftForm.dbc` | L1 ref | 35 | 140 | 61 | ok | core DBCfmt `SpellShapeshiftFormEntryfmt` (14/35 named) + repack (L1) |
| `0x094A` | SPELL_ICON | `SpellIcon.dbc` | L1 ref | 2 | 8 | 16396 | ok | none found — ref: stock (wowdev, L1) |
| `0x094B` | TALENT | `Talent.dbc` | L1 ref | 23 | 92 | 2384 | ok | core DBCfmt `TalentEntryfmt` (12/23 named) + repack (L1) |
| `0x094C` | TALENT_TAB | `TalentTab.dbc` | L1 ref | 24 | 96 | 37 | ok | core DBCfmt `TalentTabEntryfmt` (4/24 named) + repack (L1) |
| `0x094D` | WORLD_SAFE_LOCS | `WorldSafeLocs.dbc` | L1 ref | 22 | 88 | 915 | ok | none found — ref: stock (wowdev, L1) |
| `0x094F` | SPELL_CATEGORY | `SpellCategory.dbc` | L1 ref | 2 | 8 | 5192 | ok | core DBCfmt `SpellCategoryfmt` (2/2 named) + repack (L1) |
| `0x0950` | SPELL_DURATION | `SpellDuration.dbc` | L1 ref | 4 | 16 | 866 | ok | core DBCfmt `SpellDurationfmt` (4/4 named) + repack (L1) |
| `0x0951` | SPELL_CAST_TIMES | `SpellCastTimes.dbc` | L1 ref | 4 | 16 | 71 | ok | core DBCfmt `SpellCastTimefmt` (2/4 named) + repack (L1) |
| `0x0952` | SPELL_RADIUS | `SpellRadius.dbc` | L1 ref | 4 | 16 | 318 | ok | core DBCfmt `SpellRadiusfmt` (4/4 named) + repack (L1) |
| `0x0953` | SPELL_RANGE | `SpellRange.dbc` | L1 ref | 40 | 160 | 323 | ok | core DBCfmt `SpellRangefmt` (6/40 named) + repack (L1) |
| `0x0954` | SPELL_DIFFICULTY | `SpellDifficulty.dbc` | L1 ref | 5 | 20 | 3811 | ok | core DBCfmt `SpellDifficultyfmt` (5/5 named) + repack (L1) |
| `0x0955` | SPELL_DESCRIPTION_VARIABLES | `SpellDescriptionVariables.dbc` | L1 ref | 2 | 8 | 31 | ok | none found — ref: stock (wowdev, L1) |
| `0x0956` | SPELL_EFFECT_CAMERA_SHAKES | `SpellEffectCameraShakes.dbc` | L1 ref | 4 | 16 | 37 | ok | none found — ref: stock (wowdev, L1) |
| `0x0957` | SPELL_CHAIN_EFFECTS | `SpellChainEffects.dbc` | L1 ref | 48 | 177 | 6636 | ok | none found — ref: stock (wowdev, L1) |
| `0x0958` | SPELL_ITEM_ENCHANTMENT_CONDITION | `SpellItemEnchantmentCondition.dbc` | L1 ref | 31 | 64 | 49 | ok | core DBCfmt `SpellItemEnchantmentConditionfmt` (26/31 named) + repack (L1) |
| `0x0959` | SPELL_VISUAL_KIT_AREA_MODEL | `SpellVisualKitAreaModel.dbc` | L1 ref | 3 | 12 | 17 | ok | none found — ref: stock (wowdev, L1) |
| `0x095A` | SPELL_VISUAL_PRECAST_TRANSITIONS | `SpellVisualPrecastTransitions.dbc` | L1 ref | 3 | 12 | 3 | ok | none found — ref: stock (wowdev, L1) |
| `0x095B` | PARTICLE_COLOR | `ParticleColor.dbc` | L1 ref | 10 | 40 | 1666 | ok | none found — ref: stock (wowdev, L1) |
| `0x095C` | GROUND_EFFECT_TEXTURE | `GroundEffectTexture.dbc` | L1 ref | 11 | 44 | 38436 | ok | none found — ref: stock (wowdev, L1) |
| `0x095D` | GROUND_EFFECT_DOODAD | `GroundEffectDoodad.dbc` | L1 ref | 3 | 12 | 1968 | ok | none found — ref: stock (wowdev, L1) |
| `0x095E` | SCREEN_EFFECT | `ScreenEffect.dbc` | L1 ref | 10 | 40 | 52 | ok | none found — ref: stock (wowdev, L1) |
| `0x095F` | SPELL_RUNE_COST | `SpellRuneCost.dbc` | L1 ref | 5 | 20 | 476 | ok | core DBCfmt `SpellRuneCostfmt` (5/5 named) + repack (L1) |
| `0x0960` | TOTEM_CATEGORY | `TotemCategory.dbc` | L1 ref | 20 | 80 | 40 | ok | core DBCfmt `TotemCategoryEntryfmt` (3/20 named) + repack (L1) |
| `0x0961` | SPELL_FOCUS_OBJECT | `SpellFocusObject.dbc` | L1 ref | 18 | 72 | 435 | ok | core DBCfmt `SpellFocusObjectfmt` (1/18 named) + repack (L1) |
| `0x0962` | CAMERA_SHAKES | `CameraShakes.dbc` | L1 ref | 8 | 32 | 89 | ok | none found — ref: stock (wowdev, L1) |
| `0x0963` | OVERRIDE_SPELL_DATA | `OverrideSpellData.dbc` | L1 ref | 12 | 48 | 49 | ok | core DBCfmt `OverrideSpellDatafmt` (11/12 named) + repack (L1) |
| `0x0964` | ITEM_VISUALS | `ItemVisuals.dbc` | L1 ref | 6 | 24 | 227 | ok | none found — ref: stock (wowdev, L1) |
| `0x0965` | ITEM_VISUAL_EFFECTS | `ItemVisualEffects.dbc` | L1 ref | 2 | 8 | 205 | ok | none found — ref: stock (wowdev, L1) |
| `0x0966` | ITEM_SET | `ItemSet.dbc` | L1 ref | 53 | 212 | 2348 | ok | core DBCfmt `ItemSetEntryfmt` (45/53 named) + repack (L1) |
| `0x0967` | ITEM_RANDOM_SUFFIX | `ItemRandomSuffix.dbc` | L1 ref | 29 | 116 | 275 | ok | core DBCfmt `ItemRandomSuffixfmt` (27/29 named) + repack (L1) |
| `0x0968` | ITEM_RANDOM_PROPERTIES | `ItemRandomProperties.dbc` | L1 ref | 24 | 96 | 10087 | ok | core DBCfmt `ItemRandomPropertiesfmt` (22/24 named) + repack (L1) |
| `0x0969` | ITEM_PURCHASE_GROUP | `ItemPurchaseGroup.dbc` | L1 ref | 26 | 104 | 1 | ok | none found — ref: stock (wowdev, L1) |
| `0x096A` | ITEM_LIMIT_CATEGORY | `ItemLimitCategory.dbc` | L1 ref | 20 | 80 | 2629 | ok | core DBCfmt `ItemLimitCategoryEntryfmt` (3/20 named) + repack (L1) |
| `0x096B` | ITEM_DISPLAY_INFO | `ItemDisplayInfo.dbc` | L1 ref | 25 | 100 | 129695 | ok | core DBCfmt `ItemDisplayTemplateEntryfmt` (2/25 named) + repack (L1) |
| `0x096C` | ITEM_COND_EXT_COSTS | `ItemCondExtCosts.dbc` | L1 ref | 4 | 16 | 1163 | ok | core DBCfmt `ItemCondExtCostsEntryfmt` (3/4 named) |
| `0x096D` | RAND_PROP_POINTS | `RandPropPoints.dbc` | L1 ref | 16 | 64 | 300 | ok | core DBCfmt `RandomPropertiesPointsfmt` (16/16 named) + repack (L1) |
| `0x096E` | SCALING_STAT_DISTRIBUTION | `ScalingStatDistribution.dbc` | L0 name | 22 | 88 | 163 | ok | core DBCfmt `ScalingStatDistributionfmt` (22/22 named) |
| `0x096F` | SCALING_STAT_VALUES | `ScalingStatValues.dbc` | L0 name | 24 | 96 | 80 | ok | core DBCfmt `ScalingStatValuesfmt` (24/24 named) |
| `0x0970` | HELMET_GEOSET_VIS_DATA | `HelmetGeosetVisData.dbc` | L1 ref | 8 | 32 | 66 | ok | none found — ref: stock (wowdev, L1) |
| `0x0971` | CREATURE_SPELL_DATA | `CreatureSpellData.dbc` | L1 ref | 9 | 36 | 803 | ok | core DBCfmt `CreatureSpellDatafmt` (5/9 named) + repack (L1) |
| `0x0972` | CREATURE_SOUND_DATA | `CreatureSoundData.dbc` | L1 ref | 38 | 152 | 10398 | ok | none found — ref: partial names (L1) |
| `0x0973` | CREATURE_MOVEMENT_INFO | `CreatureMovementInfo.dbc` | L1 ref | 2 | 8 | 258 | ok | none found — ref: stock (wowdev, L1) |
| `0x0974` | CREATURE_MODEL_DATA | `CreatureModelData.dbc` | L0 name | 28 | 112 | 35501 | ok | lua-keys `f_100b39f0` |
| `0x0975` | CREATURE_DISPLAY_INFO_EXTRA | `CreatureDisplayInfoExtra.dbc` | L0 name | 21 | 84 | 23351 | ok | core DBCfmt `CreatureDisplayInfoExtrafmt` (2/21 named) |
| `0x0976` | CREATURE_DISPLAY_INFO | `CreatureDisplayInfo.dbc` | L0 name | 16 | 64 | 84488 | ok | core DBCfmt `CreatureDisplayInfofmt` (4/16 named) |
| `0x0977` | NPCSOUNDS | `NPCSounds.dbc` | L0 name | 5 | 20 | 2487 | ok | none found |
| `0x0978` | UNIT_BLOOD | `UnitBlood.dbc` | L0 name | 10 | 40 | 21 | ok | none found |
| `0x0979` | UNIT_BLOOD_LEVELS | `UnitBloodLevels.dbc` | L0 name | 4 | 16 | 21 | ok | none found |
| `0x097A` | VEHICLE | `Vehicle.dbc` | L1 ref | 40 | 160 | 614 | ok | core DBCfmt `VehicleEntryfmt` (38/40 named) + repack (L1) |
| `0x097B` | VEHICLE_SEAT | `VehicleSeat.dbc` | L1 ref | 58 | 232 | 1030 | ok | core DBCfmt `VehicleSeatEntryfmt` (46/58 named) + repack (L1) |
| `0x097C` | VEHICLE_UIINDICATOR | `VehicleUIIndicator.dbc` | L1 ref | 2 | 8 | 21 | ok | none found — ref: stock (wowdev, L1) |
| `0x097D` | VEHICLE_UIIND_SEAT | `VehicleUIIndSeat.dbc` | L1 ref | 5 | 20 | 35 | ok | none found — ref: stock (wowdev, L1) |
| `0x097E` | GAME_OBJECT_DISPLAY_INFO | `GameObjectDisplayInfo.dbc` | L0 name | 19 | 76 | 120871 | ok | core DBCfmt `GameObjectDisplayInfofmt` (8/19 named) |
| `0x097F` | GAME_OBJECT_ART_KIT | `GameObjectArtKit.dbc` | L1 ref | 8 | 32 | 18 | ok | core DBCfmt `GameObjectArtKitfmt` (1/8 named) + repack (L1) |
| `0x0980` | OBJECT_EFFECT_PACKAGE_ELEM | `ObjectEffectPackageElem.dbc` | L1 ref | 4 | 16 | 198 | ok | none found — ref: stock (wowdev, L1) |
| `0x0981` | OBJECT_EFFECT_MODIFIER | `ObjectEffectModifier.dbc` | L1 ref | 8 | 32 | 11 | ok | none found — ref: stock (wowdev, L1) |
| `0x0982` | OBJECT_EFFECT_PACKAGE | `ObjectEffectPackage.dbc` | L1 ref | 2 | 8 | 30 | ok | none found — ref: stock (wowdev, L1) |
| `0x0983` | OBJECT_EFFECT | `ObjectEffect.dbc` | L1 ref | 12 | 48 | 160 | ok | none found — ref: stock (wowdev, L1) |
| `0x0984` | OBJECT_EFFECT_GROUP | `ObjectEffectGroup.dbc` | L1 ref | 2 | 8 | 111 | ok | none found — ref: stock (wowdev, L1) |
| `0x0985` | SOUND_WATER_TYPE | `SoundWaterType.dbc` | L1 ref | 4 | 16 | 12 | ok | none found — ref: stock (wowdev, L1) |
| `0x0986` | SOUND_PROVIDER_PREFERENCES | `SoundProviderPreferences.dbc` | L1 ref | 24 | 96 | 32 | ok | none found — ref: stock (wowdev, L1) |
| `0x0987` | SOUND_SAMPLE_PREFERENCES | `SoundSamplePreferences.dbc` | L1 ref | 17 | 68 | 2 | ok | none found — ref: stock (wowdev, L1) |
| `0x0988` | SOUND_FILTER | `SoundFilter.dbc` | L1 ref | 2 | 8 | 20 | ok | none found — ref: stock (wowdev, L1) |
| `0x0989` | SOUND_FILTER_ELEM | `SoundFilterElem.dbc` | L1 ref | 13 | 52 | 51 | ok | none found — ref: stock (wowdev, L1) |
| `0x098A` | SOUND_ENTRIES_ADVANCED | `SoundEntriesAdvanced.dbc` | L1 ref | 24 | 96 | 18812 | ok | none found — ref: stock (wowdev, L1) |
| `0x098B` | SOUND_ENTRIES | `SoundEntries.dbc` | L1 ref | 30 | 120 | 45870 | ok | core DBCfmt `SoundEntriesfmt` (1/30 named) + repack (L1) |
| `0x098C` | SOUND_EMITTERS | `SoundEmitters.dbc` | L1 ref | 10 | 40 | 632 | ok | none found — ref: stock (wowdev, L1) |
| `0x098D` | SOUND_AMBIENCE | `SoundAmbience.dbc` | L1 ref | 3 | 12 | 242 | ok | none found — ref: stock (wowdev, L1) |
| `0x098E` | VOCAL_UISOUNDS | `VocalUISounds.dbc` | L1 ref | 7 | 28 | 641 | ok | none found — ref: stock (wowdev, L1) |
| `0x098F` | UISOUND_LOOKUPS | `UISoundLookups.dbc` | L1 ref | 3 | 12 | 130 | ok | none found — ref: stock (wowdev, L1) |
| `0x0990` | ZONE_MUSIC | `ZoneMusic.dbc` | L1 ref | 8 | 32 | 496 | ok | none found — ref: stock (wowdev, L1) |
| `0x0991` | ZONE_INTRO_MUSIC_TABLE | `ZoneIntroMusicTable.dbc` | L1 ref | 5 | 20 | 179 | ok | none found — ref: stock (wowdev, L1) |
| `0x0992` | WORLD_STATE_ZONE_SOUNDS | `WorldStateZoneSounds.dbc` | L1 ref | 8 | 32 | 42 | ok | none found — ref: stock (wowdev, L1) |
| `0x0993` | WORLD_CHUNK_SOUNDS | `WorldChunkSounds.dbc` | L1 ref | 9 | 36 | 0 | ok | none found — ref: stock (wowdev, L1) |
| `0x0994` | SHEATHE_SOUND_LOOKUPS | `SheatheSoundLookups.dbc` | L1 ref | 7 | 28 | 33 | ok | none found — ref: stock (wowdev, L1) |
| `0x0995` | BATTLEMASTER_LIST | `BattlemasterList.dbc` | L1 ref | 32 | 128 | 73 | ok | core DBCfmt `BattlemasterListEntryfmt` (28/32 named) + repack (L1) |
| `0x0996` | LOCK_TYPE | `LockType.dbc` | L1 ref | 53 | 212 | 25 | ok | none found — ref: stock (wowdev, L1) |
| `0x0997` | FACTION_GROUP | `FactionGroup.dbc` | L1 ref | 20 | 80 | 4 | ok | none found — ref: stock (wowdev, L1) |
| `0x0998` | AREA_TRIGGER | `AreaTrigger.dbc` | L1 ref | 10 | 40 | 1486 | ok | none found — ref: stock (wowdev, L1) |
| `0x0999` | AREA_POI | `AreaPOI.dbc` | L1 ref | 54 | 216 | 847 | ok | core DBCfmt `AreaPOIEntryfmt` (18/54 named) + repack (L1) |
| `0x099A` | AREA_GROUP | `AreaGroup.dbc` | L1 ref | 8 | 32 | 304 | ok | core DBCfmt `AreaGroupEntryfmt` (8/8 named) + repack (L1) |
| `0x099B` | LFGDUNGEON_GROUP | `LFGDungeonGroup.dbc` | L1 ref | 21 | 84 | 18 | ok | none found — ref: stock (wowdev, L1) |
| `0x099C` | LFGDUNGEON_EXPANSION | `LFGDungeonExpansion.dbc` | L1 ref | — | — | — | **absent** | none found — ref: stock (wowdev, L1) |
| `0x099D` | WORLD_STATE_UI | `WorldStateUI.dbc` | L1 ref | 63 | 252 | 266 | ok | none found — ref: stock (wowdev, L1) |
| `0x099E` | QUEST_FACTION_REWARD | `QuestFactionReward.dbc` | L1 ref | 11 | 44 | 2 | ok | core DBCfmt `QuestFactionRewardfmt` (11/11 named) + repack (L1) |
| `0x099F` | QUEST_INFO | `QuestInfo.dbc` | L1 ref | 18 | 72 | 11 | ok | none found — ref: partial names (L1) |
| `0x09A0` | QUEST_SORT | `QuestSort.dbc` | L1 ref | 18 | 72 | 144 | ok | core DBCfmt `QuestSortEntryfmt` (1/18 named) + repack (L1) |
| `0x09A1` | QUEST_XP | `QuestXP.dbc` | L1 ref | 11 | 44 | 100 | ok | core DBCfmt `QuestXPfmt` (11/11 named) + repack (L1) |
| `0x09A2` | SKILL_COSTS_DATA | `SkillCostsData.dbc` | L1 ref | 5 | 20 | 1500 | ok | none found — ref: stock (wowdev, L1) |
| `0x09A3` | SKILL_LINE_CATEGORY | `SkillLineCategory.dbc` | L1 ref | 19 | 76 | 9 | ok | none found — ref: stock (wowdev, L1) |
| `0x09A4` | SKILL_TIERS | `SkillTiers.dbc` | L1 ref | 33 | 132 | 26 | ok | core DBCfmt `SkillTiersfmt` (17/33 named) + repack (L1) |
| `0x09A5` | TAXI_NODES | `TaxiNodes.dbc` | L1 ref | 24 | 96 | 401 | ok | core DBCfmt `TaxiNodesEntryfmt` (23/24 named) + repack (L1) |
| `0x09A6` | TAXI_PATH | `TaxiPath.dbc` | L1 ref | 4 | 16 | 947 | ok | core DBCfmt `TaxiPathEntryfmt` (4/4 named) + repack (L1) |
| `0x09A7` | TAXI_PATH_NODE | `TaxiPathNode.dbc` | L1 ref | 11 | 44 | 23314 | ok | core DBCfmt `TaxiPathNodeEntryfmt` (11/11 named) + repack (L1) |
| `0x09A8` | DUNGEON_MAP | `DungeonMap.dbc` | L1 ref | 8 | 32 | 204 | ok | none found — ref: stock (wowdev, L1) |
| `0x09A9` | DUNGEON_MAP_CHUNK | `DungeonMapChunk.dbc` | L1 ref | 5 | 20 | 2726 | ok | none found — ref: stock (wowdev, L1) |
| `0x09AA` | WORLD_MAP_AREA | `WorldMapArea.dbc` | L1 ref | 11 | 44 | 310 | ok | core DBCfmt `WorldMapAreaEntryfmt` (7/11 named) + repack (L1) |
| `0x09AB` | WORLD_MAP_CONTINENT | `WorldMapContinent.dbc` | L1 ref | 14 | 56 | 4 | ok | none found — ref: stock (wowdev, L1) |
| `0x09AC` | WORLD_MAP_OVERLAY | `WorldMapOverlay.dbc` | L1 ref | 17 | 68 | 1068 | ok | core DBCfmt `WorldMapOverlayEntryfmt` (5/17 named) + repack (L1) |
| `0x09AD` | WORLD_MAP_TRANSFORMS | `WorldMapTransforms.dbc` | L1 ref | 10 | 40 | 12 | ok | none found — ref: stock (wowdev, L1) |
| `0x09AE` | TRANSPORT_ANIMATION | `TransportAnimation.dbc` | L1 ref | 7 | 28 | 5422 | ok | core DBCfmt `TransportAnimationfmt` (6/7 named) + repack (L1) |
| `0x09AF` | TRANSPORT_PHYSICS | `TransportPhysics.dbc` | L1 ref | 11 | 44 | 7 | ok | none found — ref: stock (wowdev, L1) |
| `0x09B0` | TRANSPORT_ROTATION | `TransportRotation.dbc` | L1 ref | 7 | 28 | 227 | ok | core DBCfmt `TransportRotationfmt` (7/7 named) + repack (L1) |
| `0x09C8` | LIGHT | `Light.dbc` | L1 ref | 15 | 60 | 1350 | ok | core DBCfmt `LightEntryfmt` (5/15 named) + repack (L1) |
| `0x09C9` | LIGHT_PARAMS | `LightParams.dbc` | L1 ref | 9 | 36 | 1141 | ok | none found — ref: stock (wowdev, L1) |
| `0x09CA` | LIGHT_SKYBOX | `LightSkybox.dbc` | L1 ref | 3 | 12 | 230 | ok | none found — ref: stock (wowdev, L1) |
| `0x09CB` | LIGHT_INT_BAND | `LightIntBand.dbc` | L1 ref | 34 | 136 | 20521 | ok | none found — ref: stock (wowdev, L1) |
| `0x09CC` | LIGHT_FLOAT_BAND | `LightFloatBand.dbc` | L1 ref | 34 | 136 | 6840 | ok | none found — ref: stock (wowdev, L1) |
| `0x09CF` | CHARACTER_CREATION_CLASS_DETAILS | `CharacterCreationClassDetails.dbc` | L3 ours | 28 | 112 | 464 | ok | none found — ref: partial names (L1) |
| `0x09D1` | CHR_CLASSES_ROLES | `ChrClassesRoles.dbc` | L3 ours | 11 | 44 | 32 | ok | none found |
| `0x09D2` | OCCLUSION_VOLUME | `OcclusionVolume.dbc` | L3 ours | 4 | 16 | 373 | ok | none found — ref: stock (wowdev, L1) |
| `0x09D3` | OCCLUSION_VOLUME_POINTS | `OcclusionVolumePoints.dbc` | L3 ours | 5 | 20 | 1529 | ok | none found — ref: stock (wowdev, L1) |

## What the buckets add up to

228 `SMSG_PATCH_*` fiches, 233 rows: five opcodes (`0x0567`, `0x0568`, `0x0691`, `0x06A9`,
`0x06ED`) write two tables each. 229 distinct DBC names, 228 of them present in the
snapshot.

| Bucket | Rows | Distinct tables |
| --- | ---: | ---: |
| `lua-keys <builder>` | 11 | 11 |
| `ui getter <file:line>` | 11 | 10 |
| `core DBCfmt` (AzerothCore already names it) | 70 | 70 |
| `repack schema (L1, unverified)` as the only source | 0 | 0 |
| `none found` | 141 | 138 |

Of the 141 `none found` rows: 70 the reference calls stock Wrath tables (published on
wowdev.wiki, `L1`, outside this repo's sources); 65 it gives partial, mostly data-derived
names for (`L1`); 6 it says nothing about at all — `0x059F ITEM_STAT` (`ItemStat.dbc`, 39
fields, 1 513 931 rows; the reference records no client handler for it), `0x05F8`
`LOADING_SCREENS`, `0x0977 NPCSOUNDS`, `0x0978 UNIT_BLOOD`, `0x0979 UNIT_BLOOD_LEVELS`,
`0x09D1 CHR_CLASSES_ROLES`.

The queue that matters is smaller than 141. Restricted to rows `patch-tables.yaml` binds
itself — the DLL's own custom tables, the ones nobody else has ever had to name — **71 of
the 92 bound rows (68 distinct tables) have no naming source at all**, and not one of them
is covered by the repack lead.

## The repack lead, and why it buys less than it looks

The reference's "Named field maps — raw DBC rows (64 tables)" section claims that for 64
patch tables the community repack's `acore_world.*_dbc` schema has exactly the client
DBC's column count, in record order. Its list is reproduced per row above as `+ repack (L1)`.

Two things can be checked from here, and were.

- **The counts.** 210 of the reference's 217 per-table dword figures equal the client
  header's `fieldCount` exactly. That is real corroboration of the manifest by an
  independent reader.
- **What it adds.** All 64 tables it claims a repack schema for are stock Blizzard tables
  — `Spell.dbc`, `Item.dbc`, `Achievement.dbc`, `Faction.dbc`, `Talent.dbc` and so on — and
  every one of them is a table AzerothCore already loads. The repack schema names nothing
  the fork does not already have in `DBCStructure.h`, and `DBCfmt.h`'s own column counts
  agree with the client headers in all 70 tables where the fork loads the table (0
  mismatches). Where it *would* add something is the `x` columns: across those 70 tables
  the core's format strings cover 1 888 columns and name 1 140 of them, 60 %. The 748
  skipped columns are the only place this `L1` lead is worth spending a verification on.

Not one of the 64 is a CoA-custom table. For the tables this atlas exists to document,
the reference offers partial, data-derived guesses, not a schema.

## Disagreements found

Between our own three sources — the DBC headers, the manifest and `patch-tables.yaml` —
**none**. Every bound row's `fields` and `record_size` in `patch-tables.yaml` equals the
manifest, and the manifest equals the file header, for all 228 tables present. That is
worth stating plainly: the generated binding is clean.

What the comparison did turn up:

1. **`~/CoaServer/dbc_clientset` is not the lab snapshot.** The task brief calls it "the
   actual client DBC files"; `client/datasets.yaml` registers it as `cointhrow-2026-09-09`,
   a third-party upload of unknown origin (`L1`). Re-reading all 219 shared tables from it:
   identical `fields` and `recordSize` everywhere, **47 tables differing in record count**
   (`Creature.dbc` 127 178 vs 127 343, `ZoneLightPoint.dbc` 336 vs 461, `SkillCard.dbc`
   7 726 vs 7 776, …). Same schema, different content generation — which is exactly the
   `working_hypothesis` already recorded on that dataset, now measured on the patch tables
   specifically. For *field counts* the two snapshots agree completely, so the column map
   is snapshot-independent; for anything about which ids exist, it is not.
2. **The reference counts dwords, not columns, and the difference is not cosmetic.** Seven
   of its 217 figures disagree with the client header, and in six of them its number is
   `recordSize / 4`:

   | Opcode | Table | header `fields` | `recordSize` | `rs/4` | reference |
   | --- | --- | ---: | ---: | ---: | ---: |
   | `0x0573` | `VanityCollection.dbc` | 76 | 308 | 77 | 77 |
   | `0x064A` | `CharacterAdvancement.dbc` | 179 | 692 | 173 | 173 |
   | `0x0691` | `AppearanceCategories.dbc` | 25 | 104 | 26 | 26 |
   | `0x06A5` | `Tutorial.dbc` | 92 | 372 | 93 | 93 |
   | `0x06AC` | `TutorialKeywords.dbc` | 64 | 260 | 65 | 65 |
   | `0x093A` | `CharStartOutfit.dbc` | 77 | 296 | 74 | 74 |
   | `0x0958` | `SpellItemEnchantmentCondition.dbc` | 31 | 64 | 16 | 16 |

   These tables have columns narrower or wider than four bytes, so `fieldCount` and
   `recordSize / 4` are different numbers and the record is **not** a dword array.
   `CharacterAdvancement.dbc` is the sharpest case: 179 columns in 692 bytes, which is
   171 four-byte columns plus 8 one-byte ones *if* every column is 4 or 1 byte — an
   arithmetic possibility, not a read: the widths must come from the handler before any
   name is assigned by position. `SpellChainEffects.dbc` is the seventh and
   worst: `recordSize` 177 is not a multiple of four at all, against 48 columns.
   Consequence for the naming pass: **on these tables, naming by dword index mis-assigns
   every column after the first narrow one**, and the reference's 64/64 count-verification
   is itself wrong for two of its own entries (`CharStartOutfit`, 74 claimed vs 77 in the
   header; `SpellItemEnchantmentCondition`, 16 vs 31) — AzerothCore's format strings give
   77 and 31, matching the client.
3. **`patch-tables.yaml` binds two opcodes that can have no fiche.** `0x01C0` and `0x0258`
   are bound to `Tutorial.dbc`, but AzerothCore names `0x01C0` `CMSG_PETITION_SIGN` and
   `0x0258` `CMSG_AUCTION_LIST_ITEMS`
   (`src/server/game/Server/Protocol/Opcodes.h:478`, `:630`), so ADR 0005's rule — and the
   linter — refuse a fiche for either. Ascension reuses the two numbers for server→client
   traffic. The binding is therefore invisible to every consumer that goes through
   `protocol/opcodes/`, and this file is currently the only place it is written down.
4. **One reference table does not exist here.** `0x099C` is claimed as
   `LFGDungeonExpansion.dbc`; there is no such file in `ascension-live-2026-09-17` and
   none in `cointhrow-2026-09-09`. Either the name is wrong or the table is not shipped.
5. **The reference does not cover 11 of our patch opcodes** — `0x05F8`, `0x096E`, `0x096F`,
   `0x0974`–`0x0979`, `0x097E`, `0x09D1`. Ten of them are the `L0 name` rows above.

## Where the next pass should go

- `0x0974 SMSG_PATCH_CREATURE_MODEL_DATA` is the cheapest win on the board: nothing binds
  it, yet `lua-keys.yaml`'s builder `f_100b39f0` already holds 24 ordered creature-model
  key names (`Flags, ModelName, SizeClass, ModelScale, BloodID, FootprintTextureID, …`)
  and `CreatureModelData.dbc` has 28 columns in 112 bytes. Binding the handler and reading
  that builder's stores would name a table outright.
- The challenge cluster is the densest cheap region: `f_1013c1a1`, `f_1013c3d3`,
  `f_1013c60f` and `f_1013c7de` share one key vocabulary across `ChallengeRequirements`,
  `ChallengeConditions`, `ChallengeRewards`, `ChallengeSpells`, `ChallengeRules` and
  `ChallengeModifiers`. Our extraction does not say which builder serves which table; the
  handlers' stores would.
- `lua_keys.py` found 22 builders. The reference cites builder addresses ours does not
  carry — `0x1016C8B0` (claimed 36 keys for the CA node), `0x100DAC40` (ChrSpecs),
  `0x100B2D20` (creature display), `0x10A2A870` (wildcard entries), `0x102F56F0`,
  `0x10A39330`. Those are `L1` pointers at *our own binary*: re-running the extractor at
  those RVAs turns them into `L3` without trusting anyone.
- For the 70 `core DBCfmt` rows, write no names. Point the fiche at the core (ADR 0005) and
  record only the 748 columns the core skips as open.
