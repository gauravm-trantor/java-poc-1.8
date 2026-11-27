#!/bin/sh
# Verify's sensitivity check for SBJ17-7: AC2 and AC3 on the PR head and on three mutants of workflow-app/pom.xml.
V="$(dirname -- "$0")"
C="$V/../vclone"
P="$C/workflow-app/pom.xml"
cp "$P" "$V/pom.head.xml"
run() {
  name=$1
  sh "$C/scripts/ci/test-order/AC2-webconfig-first.sh" > "$V/sens-$name-AC2.txt" 2>&1; a2=$?
  sh "$C/scripts/ci/test-order/AC3-reports-inside-target.sh" > "$V/sens-$name-AC3.txt" 2>&1; a3=$?
  echo "$name AC2=$a2 AC3=$a3 | $(tail -1 "$V/sens-$name-AC2.txt") | $(grep -a 'AC3 \(passed\|FAILED\)' "$V/sens-$name-AC3.txt")"
}
run head
# m1: the whole change removed (main's pom)
git -C "$C" show origin/main:workflow-app/pom.xml > "$P"; run m1-main-pom
# m2: report.dir line removed, temp folder kept
grep -v '<report.dir>' "$V/pom.head.xml" > "$P"; run m2-no-reportdir
# m3: temp folder removed from argLine, report.dir kept
sed 's|<argLine>@{argLine} "-Djava.io.tmpdir=${project.build.directory}"</argLine>|<argLine>@{argLine}</argLine>|' "$V/pom.head.xml" > "$P"; run m3-no-tmpdir
cp "$V/pom.head.xml" "$P"
git -C "$C" status --short
