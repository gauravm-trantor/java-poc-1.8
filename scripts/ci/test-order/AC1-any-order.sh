#!/bin/sh
# AC1 The workflow-app tests pass in alphabetical, reverse alphabetical and random order,
# each run starting from an empty temp folder.
# Usage: AC1-any-order.sh alphabetical|reversealphabetical|random
. "$(dirname -- "$0")/common.sh"

order="${1:?give the run order: alphabetical, reversealphabetical or random}"
fresh_temp
log="$CHECK_TMP/AC1-$order.log"
run_workflow_tests "$order" "$WORKFLOW_TESTS" "$log"
status=$?
ran=$(tests_ran)
echo "AC1 $order: Maven exit $status, $ran workflow-app tests ran"
if [ "$status" -ne 0 ]; then echo "AC1 FAILED: a test failed in $order order"; exit 1; fi
if [ "$ran" -lt 30 ]; then echo "AC1 FAILED: expected at least 30 workflow-app tests, $ran ran"; exit 1; fi
echo "AC1 passed in $order order"
