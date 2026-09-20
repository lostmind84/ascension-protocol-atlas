# Delta: `coa-extensions-rev4-2026-09-14` vs `ascension-extensions-2026-08-13`

## Why this matters

Third-party addresses — `azerothcore-wotlk-coa#4128` quotes `0x102FC6C0`, `0x10166899`,
`0x10151480`, `0x101742C0`, `0x10151DF0` — were read from a stock `Extensions.dll`. Our
lab client runs a CoA-patched one. If the patch had moved code, none of those addresses
would be usable in the lab and every binary fact would have to be re-derived.

It did not. **They carry across**, with ten known exceptions.

## Image identity

Both are PE32 / i386 with **`ImageBase = 0x10000000`**, so an observed absolute address
converts to an RVA by subtracting `0x10000000`. `0x10166899` is RVA `0x00166899`.

This unblocks the conversion ADR 0003 requires — for addresses that came from a build
with this same base, which remains the open question on the fiches.

## Section table

Identical for all six stock sections, same RVA, same raw size:

| Section | RVA | Raw bytes identical? |
| --- | --- | --- |
| `.text` | `0x00001000` | **no** — 30 bytes differ |
| `.rdata` | `0x00b19000` | yes |
| `.data` | `0x00bc9000` | yes |
| `.rsrc` | `0x00d3e000` | yes |
| `.reloc` | `0x00d3f000` | yes |
| `.vm_sec` | `0x00d6d000` | yes |
| `.local` | `0x00d76000` | **added by the patch** (0x51 bytes) |

Nothing was relocated: `.text` keeps its RVA, its virtual size (`0x00b1795b`) and its raw
size. The patch works by overwriting bytes in place and appending a section.

## The ten patch sites

30 bytes in `.text`, in ten contiguous runs. Addresses are RVA, with the loaded VA at
`ImageBase 0x10000000` alongside.

| RVA | VA | Stock | Patched |
| --- | --- | --- | --- |
| `0x000e3dc0` | `0x100e3dc0` | `55 8b ec 6a ff` | `e9 3b 22 c9 00` |
| `0x000e5d70` | `0x100e5d70` | `56 8b f1 e8 58` | `e9 ab 02 c9 00` |
| `0x000e5dd0` | `0x100e5dd0` | `55 8b ec 83 e4` | `e9 6b 02 c9 00` |
| `0x00195499` | `0x10195499` | `75` | `eb` |
| `0x001b0b00` | `0x101b0b00` | `56 b8 f0` | `b0 01 c3` |
| `0x001b4b3d` | `0x101b4b3d` | `75` | `eb` |
| `0x001b5aba` | `0x101b5aba` | `83 7f 30` | `e9 71 00` |
| `0x001b5abe` | `0x101b5abe` | `74 10` | `00 90` |
| `0x002fc620` | `0x102fc620` | `8a 41 48 c3` | `b0 01 c3 90` |
| `0x00a3cb4d` | `0x10a3cb4d` | `74` | `eb` |

The shapes are what they look like: three function prologues replaced by `jmp` into the
appended section, four conditional jumps forced (`75`/`74` to `eb`), and two functions
stubbed to `mov al,1; ret`.

**Note:** the site at VA `0x102fc620` sits 160 bytes below `0x102FC6C0`, the address
`#4128` gives for the `SMSG 0x09BC` handler. Nearby, not the same. Whether the patched
function and the handler are related is unexamined — worth checking before trusting
`0x09BC` observations made on the patched build.

## Consequence for the atlas

- A binary fact established in the lab holds for `coa-extensions-rev4-2026-09-14`. It
  transfers to the stock build for every RVA outside the ten sites above.
- A fact touching one of those sites must say which build it was observed on.
- Prefer disassembling the **stock** build; prefer observing the **patched** one, since
  that is what runs. Where the two disagree, this table says why.

## Reproduce

```sh
python3 tools/extract/peinfo.py <client>/Extensions.dll.ORIGINAL <client>/Extensions.dll
python3 tools/extract/peinfo.py --compare \
    <client>/Extensions.dll.ORIGINAL <client>/Extensions.dll
```

Every table above is that command's output.
