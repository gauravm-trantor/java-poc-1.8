# Shared steps for the test-order checks of card SBJ17-7. Sourced by the AC scripts beside it.
# Design: docs/cards/SBJ17-7.md, section Plan.

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
WORKFLOW_TESTS='com/example/salesbatch/workflow/**/*Test'

# Start from an empty temp folder, so no report left by an earlier run can make a test pass.
# Java on Windows reads TMP/TEMP; Java on Linux always uses /tmp, so the report folders there are removed.
fresh_temp() {
  rm -rf /tmp/sales-batch-test-reports /tmp/sales-batch-reports /tmp/sales-batch-uploads
  if [ -d /c/tmp ]; then rm -rf /c/tmp/sales-batch-reports; fi
  CHECK_TMP=$(mktemp -d)
  if command -v cygpath >/dev/null 2>&1; then win_tmp=$(cygpath -w "$CHECK_TMP"); else win_tmp="$CHECK_TMP"; fi
  export TMP="$win_tmp" TEMP="$win_tmp" TMPDIR="$CHECK_TMP"
  echo "Empty temp folder: $CHECK_TMP"
}

# run_workflow_tests <surefire run order> <test pattern> <log file>
# Never passes argLine or report.dir: that would override what the build sets.
run_workflow_tests() {
  mvn -B -f "$ROOT/pom.xml" clean test -pl workflow-app -am \
    "-Dtest=$2" -DfailIfNoTests=false "-Dsurefire.runOrder=$1" > "$3" 2>&1
  status=$?
  grep -aE "Running com\.example|Tests run:|FAIL|ERROR\]" "$3" | grep -av "^\s*at " | cut -c1-240
  return $status
}

# Number of workflow-app tests that ran, from the Surefire reports.
tests_ran() {
  total=0
  for f in "$ROOT"/workflow-app/target/surefire-reports/TEST-*.xml; do
    [ -f "$f" ] || continue
    n=$(grep -o '<testsuite[^>]* tests="[0-9]*"' "$f" | head -1 | sed 's/.* tests="\([0-9]*\)"/\1/')
    total=$((total + ${n:-0}))
  done
  echo "$total"
}
