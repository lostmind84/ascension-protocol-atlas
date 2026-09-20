# The wire path: from Ascension.exe's socket to Extensions.dll's handlers and back

What sits between a `WorldPacket` the server writes and the Lua event the UI receives,
read from the two binaries (`GHIDRA_PROGRAM=Ascension.exe.ORIGINAL tools/ghidra/ghidra.sh
run Decomp.java <VA>` for the exe, the usual wrapper for the DLL). Everything here is
`L3`: an address and a decompilation, no capture. Function names are ours, chosen from
what the code does; the binaries carry none.

## 1. The exe loads the DLL

Stock `Ascension.exe` is `Wow.exe` 3.3.5a (12340) with one entry patch: the small
function at `0x0040b7d0` starts with `jmp 0x4e5cb0`, a code cave that sets
`DAT_00b6b474 := 1`, calls `LoadLibraryA("Extensions.dll")` (the string lives at
`0x004e5ce0`, inside `.text`), runs the displaced prologue and jumps back to `0x0040b7d8`.
The exe imports nothing from the DLL; the DLL exports one dummy symbol
(`ClientExtensionsDummy`) and does all its wiring from `DllMain`.

## 2. The DLL patches and detours the exe

`FUN_102c3540` (Extensions.dll) is the installer. It resolves `NtProtectVirtualMemory`
by walking the PEB's module exports with an FNV-1a hash (`0xcbfe435b` seed, target
`0xf0adcb54`), unprotects one dword and writes:

| Exe address | Stock | Patched | Effect |
| --- | --- | --- | --- |
| `0x0063200d` | `0x51f` | `0x9d4` | the immediate of `cmp esi, 0x51f` in `ClientServices::ProcessMessage`: the opcode bound becomes `0x9d4`, the size of the DLL's own name table (`opcodes.yaml`, 2517 entries) |

Then it installs five detours (`FUN_100010f0`, a trampoline allocator that returns the
original entry) on exe functions whose addresses sit in the DLL's `.data`:

| Exe function | Detour in the DLL | Role |
| --- | --- | --- |
| `0x00631fa0 ClientServices::SetMessageHandler(opcode, handler, param)` | `FUN_102c4400` | registrar: opcode `> 0x55e` goes into the DLL's own map (`FUN_100bd860`, handler at `+0xc`); otherwise the original, through the vtable slot `+4` |
| `0x00631fc0 ClientServices::ClearMessageHandler(opcode)` | `LAB_102c3f80` | the mirror |
| `0x00631fe0 ClientServices::ProcessMessage(param, packet)` | `FUN_102c3ab0` | **incoming dispatch**: `Get(u16)` the opcode, FNV-1a hash it, look the DLL map up; a miss logs `Skipped packet: %s (%u)`; a hit calls the handler with the `CDataStore` positioned after the opcode. With logging on, `{} (0x{:08X})` and timing go to the packet log |
| `0x00632b50 ClientServices::Send(packet)` | `FUN_102c3ff0` | **outgoing hook**: reads the u16 opcode at the start of the store, logs `SENT {} (0x{:08X})` when logging is on, special-cases the movement opcodes (`0xa9`, `0xb5`–`0xc3`, `0xc9`–`0xcb`, `0xda`, `0xdb`, `0xdd`, `0xee`, `0x2ae`), resets the read pos and hands the store to `FUN_100e0ca0`, which reaches the original |
| `0x00632a40 ClientServices::ClientServices()` | `LAB_102c3a90` | constructor hook |

## One packet family is compressed

`SMSG 0x06AA` (the Hand of Fate rewards list) does not carry its records in the clear: the
payload is a `u32` uncompressed size followed by a deflate stream, and the handler's reader
(`FUN_10195a60`) copies the rest of the store and calls the executable's zlib
`uncompress` at `0x00778180` before anything is parsed. That function is zlib 1.2.2
(`inflateInit_`, `inflate(Z_FINISH)`, `inflateEnd`) with a 47 000-byte output window, so a
record set that inflates past that window is refused with `Z_BUF_ERROR`.

It is the only compressed Ascension packet found so far. A server that wants to send this
list has to deflate the payload; sending it in the clear reaches `inflate` and fails.

So every packet the exe receives passes through the DLL first, and every packet the DLL
sends passes through the exe's `Send`. The stock handler tables (`[ClientServices +
0x53c + opcode*4]` for the function, `+0x19b8` for its parameter) still serve the stock
opcodes below `0x55f`; above, the DLL's hash map does (`handlers.yaml` lists the 532
registrations, `registration_site_rva` being the call into the registrar).

## 3. `CDataStore`, the packet object

`Extensions.dll` never touches the buffer itself: it calls the exe through a static
pointer table at `0x10bc90a0..` (`exe-pointer-table.yaml`, 461 slots, 44 labelled). The
object (`0x00401050`): `+0` vtable `0x009e0e24`, `+4` buffer, `+8` base, `+0xc` capacity,
`+0x10` size (write position), `+0x14` read position (`-1` until `Finalize`).

| Slot | Exe | Does |
| --- | --- | --- |
| `0x10bc90bc` | `0x00401050` | constructor |
| `0x10bc90c0` / `c4` / `cc` / `d0` / `d4` | `0x47afe0` / `47b040` / `47b0a0` / `47b100` / `47b160` | `Put` u8 / u16 / u32 / u64 / float |
| `0x10bc90dc` | `0x0047b1c0` | `PutData(ptr, size)` |
| `0x10bc90d8` | `0x0047b300` | `PutString(cstr)`: `PutData(cstr, strlen + 1)` — NUL included |
| `0x10bc90fc` | `0x00401130` | **`Finalize`**: read position `:= 0`. Not the send. |
| `0x10bc91e8` → `0x10bc91ec` | `0x00406f40` → `0x00632b50` | `SendPacket` → `ClientServices::Send` |
| `0x10bc9100` | `0x00403880` | destructor |
| `0x10bc90e0` / `e4` / `e8` / `ec` / `f0` | `0x47b340` / `47b380` / `47b3c0` / `47b400` / `47b440` | `Get` u8 / u16 / u32 / u64 / float |
| `0x10bc90f4`, `0x10bc90f8` | `0x0047b480`, `0x0047b560` | `GetString(buf, max)`, `GetData(ptr, size)` |

**Correction (2026-09-19).** `client/client-senders.md` first read `0x10bc90fc` as "send".
It is `Finalize`; the send is the pair `0x10bc91e8`/`0x10bc91ec` that follows it in every
sender (`ToggleDraftMode`: `(*DAT_10bc90fc)(); (*DAT_10bc91e8)(&store);`). The layouts
were not affected — the scan used `0x10bc90fc` as "the last Put is behind us", which is
still true — and the table there now says so.

A sender therefore is: constructor → `Put(u32 opcode)` → `Put*`/`PutData`/`PutString`
per field → `Finalize` → `SendPacket` → destructor. The u32 opcode in the store is what
`ClientServices::Send` turns into the 6-byte client header (u16 size, u32 opcode) before
the header cipher, in the exe (`0x00632b50` → `0x0047b280` when `+0x538` is set).

A handler receives the store with the read position just after the u16 opcode
`ProcessMessage` consumed, so every layout in the fiches starts at the first payload
byte — which the Lua `RegisterPacket` callback confirmed (`client/lua-packet-api.md`:
`GetUInt8` returned the payload first).

## 4. Strings on the wire

Three idioms, all in `handler-fire.yaml`'s `reads`:

| Type | Client reads | Server writes |
| --- | --- | --- |
| `cstring` | scan to the NUL (`do { } while (c != 0)` on the cursor) or `GetString` | `WorldPacket << std::string` (NUL appended), `SendResult` |
| `lpstring` | `FUN_100d3680`: `u32 length`, then that many bytes, into a `std::string`; or the same inline (`u32`, `memcpy`) | `AppendConfigString` (u32 size, bytes) or `<< uint32(size + 1); append(...)` (NUL counted in the length) |
| `bytes_N` | a block copy of N bytes into a struct | N bytes written field by field |

## 5. What the CoA client patch changes in the exe

`client/builds/coa-exe-rev4-2026-09-14.delta.md`: four code patches, the realmlist
string, the manifest, and a new `.local` section carrying the trampolines. None of them
touches the wire path above.
