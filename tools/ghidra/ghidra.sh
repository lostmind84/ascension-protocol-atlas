#!/usr/bin/env bash
# Ghidra headless wrapper for the atlas. Three verbs:
#
#   tools/ghidra/ghidra.sh import <Extensions.dll>        one-time analysis (~30 min)
#   tools/ghidra/ghidra.sh run <Script.java> [args...]    run a script from tools/ghidra/scripts
#   tools/ghidra/ghidra.sh farm <N> <addrs> <outdir>      decompile an address list on N workers
#
# The project lives in build/ghidra (gitignored). Script arguments are virtual addresses in
# hex without 0x, e.g. `run Decomp.java 10171260`. Output goes to stdout, stripped of
# Ghidra's log prefixes. GHIDRA_PROGRAM selects the program (default Extensions.dll;
# Ascension.exe.ORIGINAL once imported).
#
# CONCURRENCY. A Ghidra project takes an exclusive lock: a second `run` against the same
# project dies in openProject, and `-readOnly` does not help. It does NOT follow that the
# work must be serialised. Measured 2026-09-20 on this machine: a run costs 3.5 s fixed and
# about 30 ms per function, and a reflink copy of the 265 MB project costs 0.15 s and no
# disk until written. So give each worker its own copy instead of queueing:
#
#   GHIDRA_WORKSPACE=agent3 tools/ghidra/ghidra.sh run DumpC.java in out
#
# creates build/ghidra-agent3 on first use and runs there. Several agents can then hold
# their own workspace and never wait on each other. `farm` does the same for one big list.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
PROJECT="atlas"
BASE_DIR="$ROOT/build/ghidra"
HEADLESS="${GHIDRA_HEADLESS:-/opt/ghidra/support/analyzeHeadless}"

workspace_dir() {
  local name="${GHIDRA_WORKSPACE:-}"
  if [[ -z "$name" ]]; then echo "$BASE_DIR"; return; fi
  local dir="$ROOT/build/ghidra-$name"
  if [[ ! -d "$dir" ]]; then
    [[ -d "$BASE_DIR" ]] || { echo "no base project at $BASE_DIR; run 'import' first" >&2; exit 1; }
    cp -a --reflink=auto "$BASE_DIR" "$dir"
  fi
  echo "$dir"
}

headless_run() {  # <project dir> <script> [args...]
  local dir="$1" script="$2"; shift 2
  "$HEADLESS" "$dir" "$PROJECT" -process "${GHIDRA_PROGRAM:-Extensions.dll}" -noanalysis \
    -scriptPath "$HERE/scripts" -postScript "$script" "$@" 2>/dev/null \
    | sed -e "s/^INFO  ${script%.java}\.java> //" -e 's/ (GhidraScript)  *$//' \
    | grep -vE '^(INFO|WARN|ERROR|DEBUG) |^\s*$|^\s+/' || true
}

[[ -x "$HEADLESS" ]] || { echo "analyzeHeadless not found at $HEADLESS (set GHIDRA_HEADLESS)" >&2; exit 1; }

case "${1:-}" in
  import)
    [[ -f "${2:-}" ]] || { echo "usage: ghidra.sh import <Extensions.dll>" >&2; exit 1; }
    mkdir -p "$BASE_DIR"
    exec "$HEADLESS" "$BASE_DIR" "$PROJECT" -import "$2" -processor x86:LE:32:default
    ;;
  run)
    [[ -n "${2:-}" ]] || { echo "usage: ghidra.sh run <Script.java> [args...]" >&2; exit 1; }
    script="$2"; shift 2
    headless_run "$(workspace_dir)" "$script" "$@"
    ;;
  farm)
    workers="${2:?usage: ghidra.sh farm <N> <addr list> <outdir>}"
    addrs="${3:?usage: ghidra.sh farm <N> <addr list> <outdir>}"
    outdir="${4:?usage: ghidra.sh farm <N> <addr list> <outdir>}"
    mkdir -p "$outdir"
    shard_dir="$(mktemp -d)"
    trap 'rm -rf "$shard_dir"' EXIT
    # round-robin so a slow function does not pile up on one worker
    awk -v n="$workers" -v d="$shard_dir" 'NF {print > (d "/shard." (NR % n))}' "$addrs"
    for shard in "$shard_dir"/shard.*; do
      ( GHIDRA_WORKSPACE="farm$(basename "$shard" | cut -d. -f2)" \
        headless_run "$(GHIDRA_WORKSPACE="farm$(basename "$shard" | cut -d. -f2)" workspace_dir)" \
        DumpC.java "$shard" "$outdir" >/dev/null ) &
    done
    wait
    echo "farm: $(ls "$outdir" | wc -l) file(s) in $outdir"
    ;;
  *)
    sed -n '2,9p' "$0" >&2; exit 1 ;;
esac
