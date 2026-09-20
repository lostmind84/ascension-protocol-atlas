#!/usr/bin/env bash
# Reject committed game assets. This repository holds observations and tools, never the
# artifacts they came from. See CONTRIBUTING.md.
set -euo pipefail

cd "$(dirname "$0")/../.."

offenders=$(git ls-files | grep -Ei '\.(mpq|dbc|dll|exe|wdb|adt|m2|blp|wmo)$' || true)

if [ -n "$offenders" ]; then
  echo "error: game assets must not be committed:" >&2
  echo "$offenders" >&2
  exit 1
fi

echo "no game assets committed"
