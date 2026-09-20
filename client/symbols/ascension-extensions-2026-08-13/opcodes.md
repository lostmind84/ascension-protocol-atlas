# Ascension's opcode table, recovered from `Extensions.dll`

Regenerate with:

```sh
python3 tools/extract/opcode_names.py <client>/Extensions.dll.ORIGINAL \
    --build ascension-extensions-2026-08-13 \
    --out client/symbols/ascension-extensions-2026-08-13/opcodes.yaml
```

## How it was recovered

The DLL has a function that turns an opcode into its name, and it is an ordinary
bounds-checked switch:

```asm
8b 44 24 04            mov  eax, [esp+4]                  ; the opcode
3d d4 09 00 00         cmp  eax, 0x9d4
0f 87 49 30 00 00      ja   default
ff 24 85 f0 7a 2c 10   jmp  dword ptr [eax*4 + 0x102c7af0] ; jump table
b8 b4 6c b4 10         mov  eax, 0x10b46cb4                ; case 0 -> "MSG_NULL"
c3                     ret
```

The jump table at VA `0x102c7af0` therefore **is** the map: its Nth entry is the case for
opcode N, and every case is a two-instruction stub loading that opcode's name. All
**2 517** cases (`0x0000`–`0x09D4`) resolve, none malformed.

`tools/extract/opcode_names.py` finds the prologue by pattern, reads the bound and the
table address out of the instructions, and walks it. No disassembler needed, and nothing
about the layout is assumed — the bound and the table address are read from the code.

## What it says

| | |
| --- | --- |
| Opcodes in the switch | **2 517** (`0x0000`–`0x09D4`) |
| Named | **2 059** |
| Answering `unknown` | **458** |
| Name identical to AzerothCore's | **1 301** |
| Named, differing from AzerothCore | **758** |
| In AzerothCore but absent here | **0** |

AzerothCore's whole 1 348-entry table is covered, and Ascension adds roughly 750 named
opcodes on top — the custom surface, now named.

## Correction: the three identities from `#4030` are right

An earlier revision of this file cast doubt on them. That doubt was wrong and is retracted.

It came from a packed blob of the same name strings elsewhere in `.rdata`, which is in its
own order — not opcode order. Reading an index from that blob as an opcode produced
offsets of `+2`, `−18` and `−18` against the published numbers, which looked like evidence
of error. It was evidence that the blob is the wrong table to read.

The switch settles it:

| Opcode | Name |
| --- | --- |
| `0x0523` | `CMSG_CUSTOM_ASCENSION_POINT_SPEND_REQUEST` |
| `0x061A` | `CMSG_CREATURE_QUERY_BULK` |
| `0x064A` | `SMSG_PATCH_CHARACTER_ADVANCEMENT` |

All three exactly as `azerothcore-wotlk-coa#4030` recorded them.

## Confirmations for `#4128`'s realm cluster

| Opcode | `#4128` called it | The client calls it |
| --- | --- | --- |
| `0x06E5` | chat-infraction notice | `SMSG_CHAT_INFRACTION` |
| `0x0926` | reset credits | `SMSG_CA_AVAILABLE_CREDITS_UPDATE` |
| `0x09BC` | realm parameters | `SMSG_REALM_INFO` |
| `0x09D0` | "flushes pending selection state" | `SMSG_CHARACTER_CUSTOMIZATION_UNLOCKS` |

The first three match his reading. The fourth does not: the name points at character
customization unlocks, not at a selection flush. Worth re-examining before that packet is
described as a reset.

## The interesting hole

The opcodes the whole CoA talent system rests on are **unnamed in the client's own table**:

```
0x071f .. 0x072d   unknown   (15 consecutive)
   including 0x0725, 0x0726, 0x0727
0x08fe .. 0x0902   unknown
   including 0x0900
0x072e             CMSG_CHARACTER_ACTIVATE
```

Yet `0x0726` demonstrably works: `tools/replay/0x0726_flag_gate.py` drives the
character-advancement container with it and the client reacts. So the client **handles an
opcode its own name table does not name**.

The 458 unnamed entries are not scattered; they form 30 contiguous runs, the longest being
`0x0802`–`0x0902` (257) and `0x0781`–`0x07ff` (127). That reads like reserved ranges in an
enum rather than names stripped one by one.

Two readings, both untested:

- the name table is generated from an enum that lags the handler code, so newer opcodes
  work without appearing in it;
- those ranges are deliberately left unnamed.

Either way the practical consequence is the same: **for this family, the name table is not
a source. The handler registration path is.** That is the next thing to find.

## Status

`L3` — read from the binary, with the extraction reproducible by the command above. Not
`L5`: only `0x0726` has been exercised against a running client. A name here is a strong
claim about intent, not proof of behaviour.
