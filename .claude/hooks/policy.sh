#!/usr/bin/env bash
set -u

script_dir="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

if command -v python3 >/dev/null 2>&1; then
  exec python3 "$script_dir/policy.py"
fi
if command -v py >/dev/null 2>&1; then
  exec py -3 "$script_dir/policy.py"
fi
if command -v python >/dev/null 2>&1; then
  exec python "$script_dir/policy.py"
fi

echo "Valiant policy: Python 3 não encontrado; operação bloqueada." >&2
exit 2
