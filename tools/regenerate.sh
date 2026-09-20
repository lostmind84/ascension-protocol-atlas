#!/usr/bin/env bash
# Rebuild every generated artifact in the atlas from its sources, in dependency order, and
# report whether anything changed. A clean `git status` afterwards is the reproducibility
# claim made concrete: someone with the same client files and core checkout gets the same
# repository. Hand-written fiches are never touched by any step.
#
#   tools/regenerate.sh <client dir> <azerothcore checkout> [<dbc set dir>]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CLIENT="${1:?client install dir, e.g. ~/CoaServer/client/ascension-live}"
CORE="${2:?azerothcore checkout}"
BUILD=ascension-extensions-2026-08-13
DLL="$CLIENT/Extensions.dll.ORIGINAL"
SYM="$ROOT/client/symbols/$BUILD"
cd "$ROOT"

python3 tools/extract/ac_baseline.py "$CORE" --out protocol/known-baseline.yaml
python3 tools/extract/opcode_names.py "$DLL" --build $BUILD --out "$SYM/opcodes.yaml"
python3 tools/extract/opcode_handlers.py "$DLL" --build $BUILD --names "$SYM/opcodes.yaml" --out "$SYM/handlers.yaml"
python3 tools/extract/lua_bindings.py "$DLL" --build $BUILD --out "$SYM/lua-bindings.yaml"
python3 tools/extract/packet_layout.py "$DLL" --build $BUILD --out "$SYM/layouts.yaml"
python3 tools/extract/client_sender.py "$DLL" --build $BUILD --out "$SYM/senders.yaml"
python3 tools/extract/exe_pointer_table.py "$DLL" --build $BUILD --out "$SYM/exe-pointer-table.yaml"
python3 tools/extract/extract_ui.py --id ascension-ui-patch-b-stock --out build/corpus/ascension-ui-patch-b-stock \
    --manifest client/corpus/ascension-ui-patch-b-stock.manifest.yaml "$CLIENT/Data/patch-B.MPQ.ORIGINAL"
python3 tools/extract/lua_enums.py build/corpus/ascension-ui-patch-b-stock --corpus ascension-ui-patch-b-stock --out protocol/enums
python3 tools/extract/event_args.py build/corpus/ascension-ui-patch-b-stock --corpus ascension-ui-patch-b-stock --out client/event-args.yaml
python3 tools/extract/sender_bindings.py "$DLL" build/corpus/ascension-ui-patch-b-stock --build $BUILD --out "$SYM/sender-bindings.yaml" \
    --functions build/ghidra/sender-functions.txt   # exact boundaries when the Ghidra run exists (FuncAt.java, see RUNBOOK)
python3 tools/extract/server_usage.py "$CORE" --out client/server-usage.yaml
python3 tools/extract/server_layout.py "$CORE" --build $BUILD --out client/server-layouts.yaml
if [[ -n "${3:-}" ]]; then
    python3 tools/extract/dbcinfo.py manifest "$3" --id ascension-live-2026-09-17 --out client/datasets/ascension-live-2026-09-17.manifest.yaml
fi
python3 tools/codegen/stub_fiches.py --build $BUILD
python3 tools/codegen/merge_layouts.py --build $BUILD
python3 tools/codegen/merge_senders.py --build $BUILD
python3 tools/codegen/merge_usage.py
python3 tools/codegen/merge_strings.py --build $BUILD   # from the committed handler-strings.yaml (Ghidra, see RUNBOOK)
python3 tools/codegen/merge_events.py
python3 tools/codegen/merge_fire.py --build $BUILD   # from the committed handler-fire.yaml (DumpC.java + handler_fire.py, see RUNBOOK)
python3 tools/codegen/merge_tables.py --build $BUILD   # from the committed result-tables.yaml
python3 tools/codegen/merge_server_names.py
python3 tools/codegen/merge_patch.py --build $BUILD   # from the committed patch-tables.yaml (patch_tables.py over the C dumps, see RUNBOOK)
python3 tools/codegen/merge_bindings.py --build $BUILD
python3 tools/codegen/index.py
python3 tools/codegen/coverage.py
python3 tools/codegen/emit.py
python3 tools/codegen/site.py
python3 tools/lint/lint_fiches.py
./tools/lint/check_no_assets.sh

echo
if git diff --quiet && git diff --cached --quiet; then
    echo "regenerate: no changes -- the repository reproduces from its sources"
else
    echo "regenerate: CHANGES -- something is not deterministic, or a source moved:"
    git status --short | head -20
    exit 1
fi
