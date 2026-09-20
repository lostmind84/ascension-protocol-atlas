# `SMSG 0x0726`: the handler, the record layout, and where the rank is not

Disassembled from the stock build with `objdump -D -b binary -m i386 -M intel` over the
bytes at each RVA. No Ghidra needed for this one.

## The path

| | RVA |
| --- | --- |
| Registered handler for opcode `0x0726` | `0x00171260` |
| Record deserializer it calls (`call` at `0x001713c4`, `ecx` = the packet) | `0x00166760` |
| The per-record read loop inside it | `0x00166899` |
| Record constructor | `0x00150020` |

`0x00166899` is the address `azerothcore-wotlk-coa#4128` publishes as the deserializer. It
is the loop entry inside the function, so the reference is right.

## The record is 32 bytes, and the wire layout is confirmed

The container is a vector of `0x20`-byte records — the code divides by `sar eax, 0x5` and
advances with `add DWORD PTR [edi+0x4], 0x20`.

The read loop reads six values in this order and stores them at these struct offsets:

| Order | Wire type | Struct offset |
| --- | --- | --- |
| 1 | `u32` | `+0x04` |
| 2 | `u32` | `+0x08` |
| 3 | `u32` | `+0x0c` |
| 4 | `u8` | `+0x10` |
| 5 | `u32` | `+0x18` |
| 6 | `u32` | `+0x1c` |

```asm
10166899:  mov  DWORD PTR [ebp-0x18],0x0
101668b9:  mov  eax,[esi+ecx*1]     ; read u32
101668c2:  mov  [ebp-0x48],eax      ;   -> +0x04
101668c5:  mov  eax,[esi+ecx*1]     ; read u32
101668ce:  mov  [ebp-0x44],eax      ;   -> +0x08
101668d1:  mov  eax,[esi+ecx*1]     ; read u32
101668da:  mov  [ebp-0x40],eax      ;   -> +0x0c
101668dd:  mov  al,BYTE PTR [esi+ecx*1] ; read u8
101668e4:  mov  BYTE PTR [ebp-0x3c],al  ;   -> +0x10
101668e7:  mov  edx,[esi+ecx*1]     ; read u32
101668ed:  mov  esi,[esi+ecx*1+0x4] ; read u32
101668fa:  mov  [ebp-0x34],edx      ;   -> +0x18
10166900:  mov  [ebp-0x30],esi      ;   -> +0x1c
```

This is exactly the six-field layout the fiche carries, so **the wire format we send is
right**. What each field means is a separate question.

## `+0x14` is a hole, and that is why the rank reads 0

The record's constructor writes the same set and nothing else:

```asm
10150020:  mov DWORD PTR [ecx],0x0
10150028:  mov DWORD PTR [ecx+0x4],0x0
1015002f:  mov DWORD PTR [ecx+0x8],0x0
10150036:  mov DWORD PTR [ecx+0xc],0x0
1015003d:  mov BYTE  PTR [ecx+0x10],0x0
10150041:  mov DWORD PTR [ecx+0x18],0x0
10150048:  mov DWORD PTR [ecx+0x1c],0x0
1015004f:  ret
```

`+0x11` through `+0x17` is untouched by both the constructor and the deserializer — a
seven-byte hole after the byte field.

`#4128` reports that `IsKnownID` requires a rank at `[+0x14]` which is neither `0` nor
`0x2c`. Whatever object that describes, **it is not this record**: nothing the packet
carries ever lands at `+0x14`.

That settles the anomaly the replay measured. `tools/replay/0x0726_flag_gate.py` and its
follow-ups put `1`, `3` and `5` in the second `u32` of a record for an entry the client
agrees is a talent, and `GetTalentRankByID` answered `0` every time. It answers `0`
because the packet has no field that reaches the rank the client reports.

## Consequence

**`SMSG 0x0726` as laid out here cannot transmit ranks.** The server can make an entry
known, and can lock it, and that is all this packet does.

So a rank has to arrive some other way, and the candidates are:

- another opcode in the unnamed block `0x071f`–`0x072d`, all of which have handlers;
- a field of `0x0725`, the slot packet sent before it (handler `0x00171d90`);
- computed client-side from the entry's own catalogue data once it is known.

This matters to the server repository directly: `mod-ascension-compat` serialises a rank
into the second `u32` of every record and has done since `#4027`. On this build that value
is stored at `+0x08` and does not reach `GetTalentRankByID`.

## Status

`L3` for the layout and the hole — read from the instructions, reproducible with the
commands above. The consequence for the rank is `L5`: it was measured against a running
client before it was explained here.
