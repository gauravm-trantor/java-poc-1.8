#!/bin/sh
# AC2 WebConfigTest run before SalesBatchProcessTest passes, from an empty temp folder.
. "$(dirname -- "$0")/common.sh"

fresh_temp
log="$CHECK_TMP/AC2.log"
# Reverse alphabetical puts WebConfigTest (W) before SalesBatchProcessTest (S).
run_workflow_tests reversealphabetical "WebConfigTest,SalesBatchProcessTest" "$log"
status=$?

web=$(grep -an "Running com.example.salesbatch.workflow.WebConfigTest" "$log" | head -1 | cut -d: -f1)
sales=$(grep -an "Running com.example.salesbatch.workflow.SalesBatchProcessTest" "$log" | head -1 | cut -d: -f1)
if [ -z "$web" ] || [ -z "$sales" ]; then echo "AC2 FAILED: both test classes must run (WebConfigTest line ${web:-none}, SalesBatchProcessTest line ${sales:-none})"; exit 1; fi
if [ "$web" -gt "$sales" ]; then echo "AC2 FAILED: WebConfigTest did not run first, so this run proves nothing"; exit 1; fi
if [ "$status" -ne 0 ]; then echo "AC2 FAILED: with WebConfigTest first, a test failed (Maven exit $status)"; exit 1; fi
echo "AC2 passed: WebConfigTest ran first and both classes passed"
