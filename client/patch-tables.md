# `SMSG_PATCH_*`: the server rewriting the client's data tables

228 of the client's custom opcodes are `SMSG_PATCH_<TABLE>`: the server pushes one record
and the client stores it in its own copy of a data table. This is how Ascension shipped
data without a client patch — spell, quest, creature, item and challenge definitions
arrive over the wire at login and overwrite what the DBC files said.

## Two kinds of table

`Extensions.dll` keeps 114 custom DBC tables of its own (`CustomDBCMgr.cpp`, the path
the DLL logs): one static object each, `0x24` bytes apart in `.data`, with the rows at
`+0x20`, `minId` at `+0x10` and `maxId` at `+0xc`. The manager loads each one with the
same idiom — a tiny getter returning `"DBFilesClient\\X.dbc"`, then `mov ecx, <object>;
call <loader>` — so the object and the file are paired by reading the manager
(`tools/extract/patch_tables.py`, `client/symbols/<build>/patch-tables.yaml`). A handler
that writes such an object, itself or through its per-table insert helper, carries one
row of that table: **87 fiches** say which (`patches_table:`), with the record size and
field count from the dataset manifest (`client/datasets.yaml`), and the block copy of
exactly that size is named `row`.

The other **141** patch handlers store into DLL-internal containers (hash maps keyed by
id, `unordered_map` in the strings) or into the executable's stock tables through the
pointer table (`client/wire-path.md`, section 3), and their record is the DLL's own
struct, not a DBC row. Their fiches keep the widths the decompilation gives; naming the
fields means reading the consumer of each container, which no pass here does.

## Reading a bound fiche

`0x056C SMSG_PATCH_MYTHIC_AFFIXES`: `row: bytes_64` = one row of `MythicAffixes.dbc`, 16
fields of 4 bytes, then nothing. `0x0591 SMSG_PATCH_CHALLENGE`: `row: bytes_84` = the
21 fixed fields of `Challenge.dbc`, followed by six `lpstring`s — the row's string
columns sent inline instead of as offsets into a string block. The order of the fixed
fields is the DBC's; the atlas has no column names for Ascension's custom tables and
does not invent them. `wxl-extended-dbc` and the preservation projects
(`docs/ROADMAP.md`, P6) are where such names may come from, at `L1`.

## What this means for a server

A CoA server that wants the client to see a changed spell, quest or challenge row sends
the row in the packet the table listens to; `client/server-layouts.md` has the four
challenge tables the fork already patches this way (`SMSG_COA_CHALLENGE_REQUIREMENT`,
...). A record the client rejects is a record outside `[minId, maxId]` of its loaded
table: the handler checks the id against the table's bounds before storing.
