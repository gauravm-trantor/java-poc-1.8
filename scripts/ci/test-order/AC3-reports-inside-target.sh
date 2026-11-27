#!/bin/sh
# AC3 The tests write no report outside the build's target/ folder.
. "$(dirname -- "$0")/common.sh"

fresh_temp
log="$CHECK_TMP/AC3.log"
run_workflow_tests alphabetical "$WORKFLOW_TESTS" "$log"
status=$?
echo "AC3: Maven exit $status (a failed test is AC1's to judge; this check looks only at where reports went)"

outside=$(
  {
    find "$CHECK_TMP" -name 'report-*.csv' 2>/dev/null
    find /tmp/sales-batch-test-reports /tmp/sales-batch-reports -name 'report-*.csv' 2>/dev/null
    if [ -d /c/tmp ]; then find /c/tmp/sales-batch-reports -name 'report-*.csv' 2>/dev/null; fi
    git -C "$ROOT" ls-files --others | grep -E '(^|/)report-[^/]*\.csv$' | grep -v '/target/' | sed "s|^|$ROOT/|"
  } | sort -u
)
inside=$(find "$ROOT/workflow-app/target" -name 'report-*.csv' 2>/dev/null)

if [ -n "$outside" ]; then echo "AC3 FAILED: reports written outside target/:"; echo "$outside"; exit 1; fi
if [ -z "$inside" ]; then echo "AC3 FAILED: no report was written at all, so this run proves nothing"; exit 1; fi
echo "AC3 passed: every report is inside workflow-app/target:"; echo "$inside"
