#!/bin/sh
# AC4 Existing tests unchanged; process file, HBase layout and run statuses unchanged (card SBJ17-11).
# That the existing tests pass is shown by the CI job (mvn -B clean test) and by AC3.
# Design: docs/cards/SBJ17-11.md, section Plan.
# Usage: AC4-unchanged.sh [base ref, default origin/main]
. "$(dirname -- "$0")/../test-order/common.sh"

base="${1:-origin/main}"
fail=0

changed=$(git -C "$ROOT" diff --name-only --diff-filter=MDRT "$base"...HEAD -- '*/src/test/*')
if [ -n "$changed" ]; then echo "AC4 FAILED: existing test files changed or removed since $base:"; echo "$changed"; fail=1
else echo "AC4: no existing test file changed since $base"; fi

kept=$(git -C "$ROOT" diff --name-only "$base"...HEAD -- workflow-app/src/main/resources/processes common/src/main spark-job/src/main)
if [ -n "$kept" ]; then echo "AC4 FAILED: the process file, the HBase layout or the Spark job changed since $base:"; echo "$kept"; fail=1
else echo "AC4: process file, HBase layout (common) and Spark job unchanged since $base"; fi

# The run statuses: every upper-case string literal in the workflow app's delegates and service.
statuses() {
  git -C "$ROOT" grep -ohE '"[A-Z][A-Z_]+"' "$1" -- ':(glob)workflow-app/src/main/java/**/delegate/*.java' ':(glob)workflow-app/src/main/java/**/service/*.java' | sort -u | tr '\n' ' '
}
before=$(statuses "$base")
after=$(statuses HEAD)
if [ "$before" != "$after" ]; then echo "AC4 FAILED: run statuses differ. Before: $before After: $after"; fail=1
else echo "AC4: run statuses unchanged: $after"; fi

[ "$fail" -eq 0 ] && echo "AC4 passed"
exit "$fail"
