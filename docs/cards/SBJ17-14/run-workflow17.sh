#!/bin/sh
# SBJ17-14 Assess probe: does workflow-app (Spring 4.3, Activiti 5.22) build and test on JDK 17 with the new data stack?
# Arg 1: compiler level for the run (17 or 1.8). Output: workflow17-<level>.log beside this script.
set -u
S="$(cd "$(dirname "$0")" && pwd)"
W="$(cygpath -m "$S" 2>/dev/null || echo "$S")"
L="${1:-17}"
MSYS_NO_PATHCONV=1 docker run --rm -v "$W/new:/src" -v sbj17-14-m2:/root/.m2 -w /src maven:3.9.9-amazoncorretto-17 \
  mvn -B -ntp clean test -pl workflow-app -am -Djava.version=$L -Dtest='!ZzProbeReportTest' -Dsurefire.failIfNoSpecifiedTests=false \
  > "$S/workflow17-$L.log" 2>&1
echo "exit $?"
grep -E "Tests run: [0-9]+, Failures: [0-9]+, Errors: [0-9]+, Skipped: [0-9]+\s*$|BUILD|Tests in error|<<< (FAIL|ERR)" "$S/workflow17-$L.log" | head -12
grep -m4 -E "Caused by|InaccessibleObject|class file|Unsupported" "$S/workflow17-$L.log"
