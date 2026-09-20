# Generated consumers

Written by `tools/codegen/emit.py` from `protocol/atlas.json`; never hand-edited (CI
checks they are current). Each carries, per opcode, the atlas's layout state and evidence
level so that a consumer sees at compile time what it is relying on.

| File | For | Use |
| --- | --- | --- |
| `ascension_opcodes.h` | `mod-ascension-compat` (C++) | `#include`, then `Ascension::Opcode::SMSG_ENTER_MANASTORM_RESULT`; replaces hand-kept `constexpr uint16` tables |
| `ascension_opcodes.go` | the Ghost harness (Go) | copy into a package `ascension`; `ascension.SmsgEnterManastormResult`, `ascension.Name[op]` |
| `ascension.lua` | Wireshark | `wireshark -X lua_script:ascension.lua` on a plaintext-header lab capture (port 8085) |

The dissector decodes only what the atlas holds: fixed widths, `cstring`, `lpstring`
(u32 length + bytes). Repeat blocks and unknown lengths stop the walk and the rest shows
as bytes. Live 3.3.5a traffic encrypts the 4/6-byte header with the session key, so it
applies to a server run with plaintext headers or to decrypted dumps.

Wiring the header into the server module is the server repository's change, not this
one's (docs/ROADMAP.md, P5).
