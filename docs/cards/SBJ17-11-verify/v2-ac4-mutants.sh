#!/bin/sh
# Verify, SBJ17-11: sensitivity of the AC4 check. Each mutant is committed in a scratch clone of the PR head,
# AC4-unchanged.sh is run against origin/main, and the clone is reset. Every mutant must make AC4 fail.
R="$1"
cd "$R" || exit 2
git config user.email verify@example.invalid; git config user.name verify
base=$(git rev-parse HEAD)
run() {
  name="$1"; shift
  "$@"
  git commit -qam "mutant $name"
  if sh scripts/ci/repeat-tests/AC4-unchanged.sh origin/main > /dev/null 2>&1; then echo "$name SURVIVED"; else echo "$name KILLED"; fi
  git reset -q --hard "$base"
}
baseline() { if sh scripts/ci/repeat-tests/AC4-unchanged.sh origin/main > /dev/null 2>&1; then echo "baseline PASS"; else echo "baseline FAIL"; fi; }
baseline
run existing-test-edited sh -c 'echo "// mutant" >> workflow-app/src/test/java/com/example/salesbatch/workflow/SalesBatchProcessTest.java'
run process-file-edited sh -c 'for f in workflow-app/src/main/resources/processes/*; do echo "<!-- mutant -->" >> "$f"; done'
run hbase-layout-edited sh -c 'f=$(git ls-files "common/src/main/*.java" | head -1); echo "// mutant" >> "$f"'
run new-status-string sh -c 'f=$(git ls-files "workflow-app/src/main/java/*service/*.java" | head -1); echo "// \"PAUSED\"" >> "$f"'
run existing-test-removed sh -c 'git rm -q workflow-app/src/test/java/com/example/salesbatch/workflow/Await.java'
