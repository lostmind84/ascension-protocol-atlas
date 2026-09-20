# Recovered packet layouts

```sh
python3 tools/extract/packet_layout.py <client>/Extensions.dll.ORIGINAL \
    --build ascension-extensions-2026-08-13 \
    --out client/symbols/ascension-extensions-2026-08-13/layouts.yaml
python3 tools/codegen/merge_layouts.py --build ascension-extensions-2026-08-13
```

## How

The client reads a packet through a cursor, and every field comes out the same way: load
from `[base + cursor]`, advance the cursor by the field's width, store it back at `+0x14`
of the packet object. Walking a handler's disassembly in address order and pairing each
load with the advance that covers it recovers the field sequence.

Two wrinkles the extractor handles, both found by getting them wrong first:

- **Which SIB register is the cursor is not visible at the instruction.** Both
  `[base+cursor*1]` and `[cursor+base*1]` occur. A pending load is remembered under both
  registers and whichever the next advance names decides it.
- **An advance can precede the loads it covers.** `0x0726`'s record loop emits
  `lea eax,[ecx+0x8]` *between* the two `u32` loads it accounts for, so unsatisfied
  advances are queued and retried after each load.

Handlers that read nothing themselves are followed one level down, into the first callee
that touches a cursor — which is how `0x0726` resolves through its deserializer at
`0x00166760`.

## Coverage

| | |
| --- | --- |
| Handlers scanned | 532 |
| Field sequences recovered | **346** |
| Handlers with no inline reads | 186 |
| Fiches updated | 329 |

The 186 are handlers that delegate more than one level, or that read through an idiom this
does not model. They are not errors, just absences.

## Known-answer checks

| Opcode | Recovered | Independently known |
| --- | --- | --- |
| `0x0725` | `u32, u32` | `#4027` reads it as a slot pair |
| `0x0726` | `u32, u32, u32, u32, u8, u32, u32` | hand-decompiled: `u32 count` + a six-field record |
| `0x0926` | `u8, u32` | `#4128`: "`u8 type`, `u32 value`" — exact |
| `0x06E5` | `u32, u32` | `#4128`: `u32`, string, `u32` — the two `u32` match, the string is invisible here |
| `0x09BC` | `u32, u32, f32, f32, f32, u32, f32, f32, u32, u8×8, cstring, u8, u32` | `#4128`: `u32`, `u32`, three floats, `u32`, two floats, `u32`, **8 gate bytes**, two strings, `u8`, `u32` — everything matches except that only one of his two strings is detected |

## What it does not tell you

- **No names and no meanings.** Fields land in the fiches as `field_0`, `field_1`. A width
  is not a semantic.
- **No structure.** A count followed by a repeated record comes out flat: `0x0726`'s seven
  fields are its count plus *one* record's six.
- **Floats are recovered**, because the client reads them with `movss` rather than `mov`:
  the width is the same as a `u32`, the opcode is what separates them. 16 fiches carry one.
- **Strings are partly recovered.** A string is not advanced by a fixed width: the client
  takes a pointer into the buffer at the cursor (`lea <r>,[base+cursor*1]`, no
  displacement) and scans for the terminator. That shape is detected and emitted as
  `cstring`, in 22 fiches. It does not catch every string — `0x09BC` has two and one is
  found, `0x06E5` has one and it is missed — so a missing `cstring` means nothing.

So a recovered layout is a **skeleton at `L3`**: the right number of fields in the right
order with the right widths, waiting for someone to say what they are.
