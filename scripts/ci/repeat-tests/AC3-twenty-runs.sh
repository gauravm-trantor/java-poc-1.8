#!/bin/sh
# AC3 The workflow app's tests pass 20 runs in a row (card SBJ17-11).
# Each run starts from an empty temp folder; the script stops at the first red run.
# Run 1 is online and fills the local Maven repository; runs 2 to 20 are offline,
# so a download refused by Maven Central cannot fail them.
# Design: docs/cards/SBJ17-11.md, section Plan.
# Usage: AC3-twenty-runs.sh [number of runs, default 20]
. "$(dirname -- "$0")/../test-order/common.sh"

runs="${1:-20}"
mvn -B -q -f "$ROOT/pom.xml" install -DskipTests || { echo "AC3 FAILED: the build before the runs failed"; exit 1; }

i=1
while [ "$i" -le "$runs" ]; do
  fresh_temp
  log="$CHECK_TMP/AC3-run-$i.log"
  if [ "$i" -eq 1 ]; then offline=""; else offline="-o"; fi
  mvn -B $offline -f "$ROOT/pom.xml" clean test -pl workflow-app > "$log" 2>&1
  status=$?
  ran=$(tests_ran)
  echo "AC3 run $i of $runs: Maven exit $status, $ran workflow-app tests ran"
  if [ "$status" -ne 0 ]; then
    grep -aE "Tests run:.*Fail|FAIL|ERROR\]" "$log" | grep -av "^\s*at " | cut -c1-240 | head -30
    echo "AC3 FAILED: run $i of $runs was red"; exit 1
  fi
  if [ "$ran" -lt 32 ]; then echo "AC3 FAILED: expected at least 32 workflow-app tests, $ran ran"; exit 1; fi
  i=$((i + 1))
done
echo "AC3 passed: $runs runs in a row"
