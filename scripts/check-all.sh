#!/usr/bin/env bash

set -u

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

status=0
contract_validation_ran=0

run_check() {
    local label="$1"
    shift
    echo "==> $label"
    if "$@"; then
        echo "PASS: $label"
    else
        echo "FAIL: $label" >&2
        status=1
    fi
}

if command -v uv >/dev/null 2>&1; then
    contract_validation_ran=1
    run_check "Contract validation" uv run --project pipeline dcviz contract-check
    run_check "Lane A Ruff" uv run --project pipeline ruff check
    run_check "Lane A pytest" uv run --project pipeline pytest
else
    echo "SKIP: Contract validation and Lane A checks (uv not found)"
fi

if [[ -d web/node_modules ]]; then
    if command -v npm >/dev/null 2>&1; then
        run_check "Lane B lint" npm --prefix web run lint
        run_check "Lane B tests" npm --prefix web test
    else
        echo "FAIL: Lane B dependencies are installed, but npm was not found" >&2
        status=1
    fi
else
    echo "SKIP: Lane B checks (web/node_modules not found)"
fi

if [[ "$contract_validation_ran" -eq 0 ]]; then
    echo "FAIL: No contract validation ran; install uv and rerun scripts/check-all.sh" >&2
    status=1
fi

exit "$status"
