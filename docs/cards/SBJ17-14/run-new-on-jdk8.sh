#!/bin/sh
# SBJ17-14 Assess probe: the EMR 7.14.0 data stack (Spark 3.5.8, Scala 2.12.18, Hadoop 3.4.2, HBase 2.6.4, ZooKeeper 3.9.3)
# compiled for and run on Java 8 (Corretto 8), whole build, no HBase container (the 2 HBase tests skip themselves).
# Copies new/ to new8/, removes the JDK 17 --add-opens argLine and sets java.version 1.8. Output: new8.log.
set -u
S="$(cd "$(dirname "$0")" && pwd)"
W="$(cygpath -m "$S" 2>/dev/null || echo "$S")"
rm -rf "$S/new8"; cp -r "$S/new" "$S/new8"; rm -rf "$S/new8"/*/target
sed -i '/<argLine>@{argLine} --add-opens/d' "$S/new8/spark-job/pom.xml"
sed -i 's#<java.version>17</java.version>#<java.version>1.8</java.version>#' "$S/new8/pom.xml"
# First run failed: shade 3.2.4 cannot read Java 21 classes in hbase-shaded-jersey's multi-release jar. Shade 3.6.0 can.
sed -i 's#<version>3.2.4</version>#<version>3.6.0</version>#' "$S/new8/pom.xml"
MSYS_NO_PATHCONV=1 docker run --rm -v "$W/new8:/src" -v sbj17-14-m2:/root/.m2 -w /src maven:3.9.9-amazoncorretto-8 \
  mvn -B -ntp clean package > "$S/new8.log" 2>&1
echo "exit $?"
grep -E "Tests run: [0-9]+, Failures: [0-9]+, Errors: [0-9]+, Skipped: [0-9]+\s*$|BUILD|<<< (FAIL|ERR)|Building jar|Tests run:.*Skipped: [1-9]" "$S/new8.log" | head -14
cat "$S/new8/spark-job/target/probe/versions.txt" 2>/dev/null
for f in "$S/old/spark-job/target/probe/"report-*.csv; do b=$(basename "$f"); cmp -s "$f" "$S/new8/spark-job/target/probe/$b" && echo "$b identical to old" || echo "$b DIFFERS from old"; done
ls -la "$S/new8/spark-job/target/"*.jar 2>/dev/null
grep -m3 -E "Caused by|UnsupportedClassVersion" "$S/new8.log"
