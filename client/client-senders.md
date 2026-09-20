# What the client sends versus what the server reads

The mirror of `client/server-layouts.md`: for every client-to-server packet the CoA server
handles, the client's sender was located and its writes read, then compared with the
server's reader.

## How the client writes a packet

Every sender has the same shape, through a table of `Wow.exe` function pointers at
`DAT_10bc90xx` (`.data`, `0x10bc90a0..`):

| Pointer | Target in `Wow.exe` | Role, from usage |
| --- | --- | --- |
| `DAT_10bc90bc` | `0x00401050` | `CDataStore` constructor |
| `DAT_10bc90cc` | `0x0047b0a0` | **`Put(u32)`** — the opcode first, and any u32 field written the same way (`(*DAT_10bc90cc)(0x67c); (*DAT_10bc90cc)((int)fVar2);` in the stable-delete-pet sender) |
| `DAT_10bc90dc` | `0x0047b1c0` | **`PutData(ptr, size)`** — the `size` argument is the field width |
| `DAT_10bc90d8` | `0x0047b300` | put a string (seen in the anti-cheat alert sender) |
| `DAT_10bc90fc` | `0x00401130` | **`Finalize`** — read position := 0; the send is `DAT_10bc91e8`/`DAT_10bc91ec` (`0x00406f40` → `0x00632b50 ClientServices::Send`) right after it, also reached through `FUN_1008e4c0(store)`. Corrected 2026-09-19 from the exe's decompilation (`client/wire-path.md`); the scan stops at `Finalize`, which still marks the last write |

So a sender's layout is the sequence of `PutData` sizes, read off the `push` immediates
before each call. Two senders write their payload through a helper instead — `0x0727`
through `FUN_10166a50`, `0x0772` through `FUN_100b97a0` — and a filtered listing shows
them as opcode-then-send with nothing between. The raw instructions show the helper call.
**A filtered listing is not evidence of an empty packet.** Twice now.

## Result

Nine packets the server parses, nine agree. Two more the server only logs; their
client-side layout is recorded so whoever implements them starts from the binary.

| Opcode | Client writes (sender) | Server reads | Verdict |
| --- | --- | --- | --- |
| `0x0727` known-entries upload | `u32 count`, then per record `4, 4, 4, 1, 8` bytes from a `0x20`-byte store record — `FUN_10166a50`, the mirror of `0x0726`'s deserializer | `ParseKnownEntriesUpload`: `u32 count`, `RECORD_SIZE` per record | agree |
| `0x061A` creature query bulk | `u32 count`, `u32 ×n` | `read<uint32>(0)`, size `4 + 4n`, entries at `4 + 4i` | agree |
| `0x0651` Manastorm enter | `u32` | size must be 4, `depth = read(0)` | agree |
| `0x0665` Manastorm leave | nothing | size must be 0 | agree |
| `0x0689` Manastorm set slot | `u32, u32` | size must be 8, `read(0)`, `read(4)` | agree |
| `0x0697` apply appearances | `u32 count`, `u32 ×n` | `>> count`, `>> appearanceId` | agree |
| `0x06A3` set can-see appearances | `u8, u8` | `>> canSeeItem >> canSeeSpell`, both `uint8` | agree |
| `0x072E` / `0x072F` character activate / deactivate | `u32` | `charGuid = read<uint32>(0)` | agree |
| `0x0772` sort order | one NUL-terminated string via `FUN_100b97a0` | `readable >> payload` | agree |
| `0x0523` point spend request | `u8, u32` | **not handled** — named for the packet log only | client layout recorded |
| `0x09C7` missile fire position | `u64, u64, u32, u8, u32 ×6` | **not parsed** — logged with `DescribePacketPayload` | client layout recorded |

`0x0727` deserves a note: `ApplyPendingBuild` (`FUN_101742c0`) is the sender, and `#4128`
reports the client-side validator refusing the build before any packet leaves. The
serializer confirms what *would* be sent: the store's records, in the `0x0726` layout.

## At scale: `tools/extract/client_sender.py`

The reading above is automated by pattern — `push <opcode>` followed by the opcode-write
call, then every `PutData` size up to the send — and validated against the twelve senders
in the table. Over every custom `CMSG`:

| | |
| --- | --- |
| Custom `CMSG` opcodes | 203 |
| Senders recovered | **158** |
| — clean layouts | 59 |
| — prefix only, a helper writes the rest (`via_helper`) | 43 |
| — empty packets | 56 |
| No sender found by this scan | 45 |

**Correction, 2026-09-19.** The first version of the scan (150 recovered) read
`DAT_10bc90cc` as an opcode-only write and stopped at its second call, so every sender
that writes a u32 through it came out as "no sender found". Decompiling the leftovers
(`tools/ghidra/scripts/SenderC.java`) showed the same call carrying a value after the
opcode. The scan now counts each further call as a `u32` and stops at a second
`CDataStore` constructor instead; it also follows the send helper `FUN_1008e4c0`. None of
the 150 layouts changed — a layout cut short by that rule was never emitted — and eight
were added: `0x0561 (u32, u32)`, `0x0613 (u64)`, `0x0667 (u32)`, `0x0679 (u32)`,
`0x067C (u32)`, `0x0744 (u32)`, `0x05E4` and `0x05E8` (the recovery tail, below).

Two helpers wrap the same calls and are modelled:

- **`FUN_100e08b0(opcode)`** — constructs the `CDataStore`, writes the opcode and sends.
  An empty packet in one call. `CMSG_CA_UNLEARN_SPELL_ALL`, `CMSG_ASCENSIONGM_TICKET_LIST_REQUEST`
  and `CMSG_TAXI_REQUEST_EARLY_LANDING` go this way.
- **`FUN_1008d690(store, opcode)`** — constructs and writes the opcode; the caller then
  `PutData`s the payload and sends. `CMSG_APPLY_RANDOM_ENCHANT_ITEM` comes out as
  `u32, u8, u8` through it.

Two more opcodes are not sent by a sender at all but registered in a **query service**
object as a request/response pair, which the service drives:

| Request | Response |
| --- | --- |
| `0x06FF CMSG_ITEM_STAT_QUERY` | `0x0700 SMSG_ITEM_STAT_QUERY_RESPONSE` |
| `0x0731 CMSG_QUEST_CACHE_ADDON_QUERY` | `0x0732 SMSG_QUEST_CACHE_ADDON_QUERY_RESPONSE` |

The pairing is read from the registration (`mov ds:[X], request; mov ds:[X+4], response`
in one case, a constructor call `(request, response, 1)` in the other). Their payload is
whatever the service serialises and is not recovered here.

## The recovery service: one binding, six opcodes

`C_RecoveryService.QueryCategory` (`FUN_10306880`) and
`C_RecoveryService.RecoverCategoryItemAtIndex` (`FUN_10306a10`) take a category *string*,
map it to an index through the table at `0x10b5a990` (`RECOVERY_SERVICE_CATEGORY_NONE`,
`_DISENCHANTED_ITEM`, `_DELETED_CHARACTER`, `_VENDORED_ITEM`, `_DELETED_ITEM`,
`_MYTHIC_RECYCLING`, `_WORLDFORGED_ITEM`, `_MAX`) and pick the opcode in a switch:

| Index | Category | Query (empty) | Recover (`u32 position`, `cstring id`) |
| --- | --- | --- | --- |
| 1 | disenchanted item | `0x05D2` | `0x05D4` |
| 2 | deleted character | `0x05DA` | `0x05DC` |
| 3 | vendored item | `0x05DE` | `0x05E0` |
| 4 | deleted item | `0x05E2` | `0x05E4` |
| 5 | mythic recycling | `0x05E6` | `0x05E8` |
| 6 | worldforged item | `0x0682` (unnamed) | `0x0684` (unnamed) |

The query is `FUN_1008d690(opcode)` then send: empty. The recover path shares one tail
(`0x10306cb5`): `PutData(&position, 4)`, `PutData(id, strlen + 1)`, `FUN_1008e4c0`. The
scan cannot follow a `jmp` into a shared tail, so these twelve are recorded by hand in
their fiches (`status: hypothetical`, sender and addresses named); `0x05E4` and `0x05E8`
happen to be reached by the linear scan falling through the case list, which is why they
also appear in `senders.yaml` with an `unknown` second width — the string length is
computed, not an immediate.

Two things worth knowing before using this. The UI's `Enum.RecoveryCategory`
(`SharedXML/Enum.lua:1592`) also has `WildCardRoll = 10`, mapped to the string
`RECOVERY_SERVICE_CATEGORY_WILDCARD_ROLLS`; that string is not in this build's table, so
the binding logs `Unexpected Value` and sends nothing — with this `Extensions.dll`, the
wildcard-roll recovery tab cannot reach the server. And `position` is not the Lua index:
the binding looks the entry up in its cached list for the category and sends the position
it found (`std::find` over a vector, offset `>> 2`), refusing the call when it is absent.

## Computed opcodes

`ToggleDraftMode(enabled)` (`FUN_100dd6e0`) writes `0x749 + (enabled == false)`: one
binding, two opcodes, `0x0749 CMSG_DRAFT_START` and `0x074A CMSG_DRAFT_STOP`, both empty.
No immediate carries either opcode, so no push-site scan finds them; their fiches are
written by hand from the arithmetic (`add eax,0x749` after `sete al`).

## The Lua packet API

The binary exposes packets to Lua directly: `CreatePacket(opcode)` (`FUN_1030f620`)
builds a `CDataStore` userdata with the opcode already written, its metatable carries
`PutUInt8/16/32`, `PutInt8/16/32`, `PutFloat`, `PutBool`, `PutString` and the matching
`Get*` plus `GetGUID`, `Send(packet)` (`0x1030fd90`) sends it, and
`RegisterPacket(opcode, fn)` (`FUN_1030fd10`) registers a Lua callback through the same
registrar the C++ handlers use (`FUN_102c4590`). `SharedXML/Util/OpcodeUtil.lua` wraps
the receiving side behind `issecure()` for the stock UI. No shipped Lua calls
`CreatePacket`, so none of the senders above goes through it — but it is the cheapest
replay tool this project has: established on a lab slot on 2026-09-19, an insecure addon
may call all of it. `client/lua-packet-api.md` has the measurements, ADR 0008 the
decision, `tools/replay/manastorm_roundtrip.py` the first `L5` pair (`0x0651`/`0x0652`).

## What the scan still does not reach

The 45 left are opcodes whose immediate is loaded but reaches no send this scan can
follow: some pass through code the pattern does not model, and four "sites" are not code
at all — `0x10441040`, `0x1044f3b0`, `0x104542b0` and `0x104e0ff0` are data embedded in
`.text` whose bytes happen to spell `mov esi, <opcode>` (`0x067C`, `0x0526`, `0x05E0`,
`0x0559` respectively); their real senders, if any, are elsewhere. Not empty, not wrong:
unread.

Thirty-three of them go further than "unread": the opcode value appears **nowhere** in
this build — not as a 32- or 16-bit immediate in `.text`, not as a 32- or 16-bit value in
`.rdata` or `.data`, not as an arithmetic constant in the window before any `Put(u32)`
that writes an opcode, and not as a number in the shipped Lua. `0x01E0` is stock 3.3.5a
under an Ascension spelling (no fiche); `0x0800 CMSG_MULTIPLE_MOVES_BETTER` is a name with
no trace either. For
these thirty-three the reading is that this build has no sender: they are names in the
table, most of them the older generation of a feature the current opcodes replaced
(`CMSG_TRANSMOG_APPLY` next to `CMSG_APPLY_APPEARANCES`, `CMSG_PGF_*` next to
`CMSG_GROUP_FINDER_*`). That last sentence is a conjecture (`L0`); the absence of any
trace is `L3` and reproducible with the searches above.

| Opcode | Name (client table) |
| --- | --- |
| `0X0520` | `CMSG_ANTICHEAT_VERSION` |
| `0X0526` | `CMSG_FEL_COMMUTATION_CHANGE_SLOT` |
| `0X0533` | `CMSG_PGF_ENLIST_GROUP` |
| `0X0534` | `CMSG_PGF_DELIST_GROUP` |
| `0X0535` | `CMSG_PGF_INVITE_GROUP_APPLICANT` |
| `0X0536` | `CMSG_PGF_DECLINE_GROUP_APPLICANT` |
| `0X0537` | `CMSG_PGF_APPLY_TO_GROUP` |
| `0X0538` | `CMSG_PGF_UNAPPLY_TO_GROUP` |
| `0X0539` | `CMSG_PGF_GROUP_LIST_REQUEST` |
| `0X053A` | `CMSG_PGF_GROUP_APPLICANT_REQUEST` |
| `0X053C` | `CMSG_ASCENSIONGM_TICKET_CHAT_REQUEST` |
| `0X053D` | `CMSG_ASCENSIONGM_TICKET_COMPLETE_REQUEST` |
| `0X0540` | `CMSG_TRANSMOG_APPLY` |
| `0X0545` | `CMSG_GET_MAIL_LIST_FORCE` |
| `0X054A` | `CMSG_ILLUSION_APPLY` |
| `0X054B` | `CMSG_REQ_RELOAD_MAP` |
| `0X054C` | `CMSG_ASCENSIONGM_TRANSACTION_LIST_REQUEST` |
| `0X054D` | `CMSG_TRANSMOG_OUTFIT_MOD_APPEARANCES` |
| `0X054E` | `CMSG_TRANSMOG_OUTFIT_MOD_NAME` |
| `0X054F` | `CMSG_TRANSMOG_OUTFIT_APPLY_ID` |
| `0X0550` | `CMSG_TRANSMOG_OUTFIT_REMOVE_ID` |
| `0X0551` | `CMSG_TRANSMOG_OUTFIT_CREATE_ID` |
| `0X0552` | `CMSG_INCARNATION_APPLY` |
| `0X0553` | `CMSG_SPELL_VISUAL_APPLY` |
| `0X0554` | `CMSG_COSMETIC_PET_APPLY` |
| `0X0555` | `CMSG_COSMETIC_APPLY` |
| `0X0557` | `CMSG_TRANSMOG_SET_SHOW_TRANSMOGRIFICATIONS` |
| `0X0558` | `CMSG_TRANSMOG_SET_SHOW_SPELL_TRANSMOGRIFICATIONS` |
| `0X0559` | `CMSG_TRANSMOG_SPEC_SET_UPDATE` |
| `0X05CD` | `CMSG_TRANSMOG_COMPONENT_APPLY` |
| `0X063E` | `CMSG_ASCENSIONGM_TICKET_HISTORY_REQUEST` |
| `0X074B` | `CMSG_DRAFT_ROLL` |
| `0X074F` | `CMSG_DRAFT_HAND_OF_FATE_START` |

## Status

Client side `L3` — decompiled, sender addresses named per fiche. Server side is the fork's
own source, `L1` for the names it lends. A `client_sender.py` that automates the
`push`/`PutData` reading is a roadmap item; these twelve were read by hand.
