#!/bin/sh
# SBJ17-14 Assess probe. Old: main d1284ca on JDK 8 (local Temurin). New: same with EMR 7.14.0 versions on Corretto 17 (Docker).
# Builds common + spark-job, runs the existing non-HBase tests and the scratch probe, then compares the probe reports.
# Usage: sh run-probe.sh   (from any folder)
set -u
S="$(cd "$(dirname "$0")" && pwd)"
for side in old new; do
  mkdir -p "$S/$side/spark-job/src/test/scala/com/example/salesbatch/spark"
  cp "$S/probe/ZzProbeReportTest.scala" "$S/$side/spark-job/src/test/scala/com/example/salesbatch/spark/"
done
TESTS='-Dtest=!SalesAggregatorHBaseTest -Dsurefire.failIfNoSpecifiedTests=false -DfailIfNoTests=false'
W="$(cygpath -m "$S" 2>/dev/null || echo "$S")"
# Both sides on Linux in Docker: the report's line ends follow the OS (Files.write), so same OS on both sides.
MSYS_NO_PATHCONV=1 docker run --rm -v "$W/old:/src" -v sbj17-14-m2:/root/.m2 -w /src maven:3.9.9-amazoncorretto-8 \
  mvn -B -ntp clean test -pl spark-job -am $TESTS > "$S/old.log" 2>&1; echo "old exit $?"
MSYS_NO_PATHCONV=1 docker run --rm -v "$W/new:/src" -v sbj17-14-m2:/root/.m2 -w /src maven:3.9.9-amazoncorretto-17 \
  mvn -B -ntp clean test -pl spark-job -am $TESTS > "$S/new.log" 2>&1; echo "new exit $?"
for side in old new; do echo "== $side"; cat "$S/$side/spark-job/target/probe/versions.txt" 2>/dev/null; grep -E "Tests run: [0-9]+, Failures: [0-9]+, Errors: [0-9]+, Skipped: [0-9]+\s*$|BUILD|ERROR\]" "$S/$side.log" | head -15; done
echo "== diff"
for f in "$S/old/spark-job/target/probe/"report-*.csv; do
  b=$(basename "$f"); if cmp -s "$f" "$S/new/spark-job/target/probe/$b"; then echo "$b identical"; else echo "$b DIFFERS"; diff "$f" "$S/new/spark-job/target/probe/$b" | head -10; fi
done
