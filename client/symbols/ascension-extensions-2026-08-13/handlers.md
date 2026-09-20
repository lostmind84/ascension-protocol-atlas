# Which opcodes the client actually handles

Regenerate with:

```sh
python3 tools/extract/opcode_handlers.py <client>/Extensions.dll.ORIGINAL \
    --build ascension-extensions-2026-08-13 \
    --names client/symbols/ascension-extensions-2026-08-13/opcodes.yaml \
    --out client/symbols/ascension-extensions-2026-08-13/handlers.yaml
```

## How

Handlers are registered with a two-argument call, emitted as three instructions:

```asm
68 90 1d 17 10    push 0x10171d90      ; the handler
68 25 07 00 00    push 0x725           ; the opcode
e8 ...            call <register>
```

Scanning `.text` for that shape yields **532** registrations across three registrar
functions (`0x002c4590` × 361, `0x002cfeb0` × 169, `0x00278530` × 2).

A name says what Ascension called an opcode. A registration says the client has code for
it. The second is the stronger statement, and the two disagree in both directions.

## Caveat

This covers `Extensions.dll` only. The standard 3.3.5a opcodes are handled by
`Ascension.exe`, so "620 SMSG names with no registration here" does **not** mean 620
unhandled packets — it means they are not handled *by this DLL*. The statement is only
sharp for opcodes outside the standard set.

## An entire unnamed block is handled

Twenty opcodes have a handler while the client's own name table answers `unknown`. Fourteen
of them are contiguous:

```
0x071f 0x0720 0x0721 0x0722 0x0723 0x0724 0x0725 0x0726
0x0728 0x0729 0x072a 0x072b 0x072c 0x072d
```

That block is the Character Advancement service: `0x0725` → handler `0x00171d90`,
`0x0726` → handler `0x00171260`. Real code, deliberately nameless. The remaining six are
`0x0683`, `0x0685`, `0x0761`, `0x0762`, `0x0765`, `0x0766`.

So for this family the name table is not a source and never was. The registration is.

## `0x0900` is not handled

`azerothcore-wotlk-coa#4128` sends a `SMSG_COA_CONFIG` on opcode `0x0900` in the login
burst, and names it as the prime candidate for the input its purchase validator is
missing.

`0x0900` has **no handler registration**, and no name. The nearest config-shaped opcode,
`0x0903 SMSG_REPLICATE_CONFIG`, has no registration either. On this build that packet
cannot be doing anything.

Worth re-checking before more is built on it — either the opcode is wrong, or the client
that observation came from is not this one.

## One of `#4128`'s addresses independently re-derived

| | |
| --- | --- |
| `#4128` publishes | `0x102FC6C0` as the `SMSG 0x09BC` handler |
| This scan finds | opcode `0x09BC` → handler RVA `0x002fc6c0` |
| With ImageBase `0x10000000` | `0x102FC6C0` |

Exact match, reached from the registration pattern with no knowledge of his figure. That
is one address of his re-derived independently — the confirmation
`client/datasets.yaml` names as what would raise the `cointhrow-2026-09-09` lineage
hypothesis above `L0`. One is not three, but it is no longer nothing.

## Selected results

| Opcode | Name | Handler RVA |
| --- | --- | --- |
| `0x0725` | *(unnamed)* | `0x00171d90` |
| `0x0726` | *(unnamed)* | `0x00171260` |
| `0x0727` | *(unnamed)* | none — client to server |
| `0x064A` | `SMSG_PATCH_CHARACTER_ADVANCEMENT` | `0x001dd650` |
| `0x06E5` | `SMSG_CHAT_INFRACTION` | `0x00114ef0` |
| `0x0900` | *(unnamed)* | **none** |
| `0x0926` | `SMSG_CA_AVAILABLE_CREDITS_UPDATE` | `0x001a1c00` |
| `0x09BC` | `SMSG_REALM_INFO` | `0x002fc6c0` |
| `0x09D0` | `SMSG_CHARACTER_CUSTOMIZATION_UNLOCKS` | `0x0032e300` |

Note `0x064A`: the server repository's talent documentation calls it "unused: the client
loads its own catalogue". It has a handler.

## Status

`L3` — read from the binary, extraction reproducible by the command above. A registration
proves code exists, not what it does.
