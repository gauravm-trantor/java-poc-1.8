#!/bin/sh
# Repeat AC2 on mutants m2 and m3, 3 times each, because the first runs hit the timing race (SBJ17-11).
V="$(dirname -- "$0")"
C="$V/../vclone"
P="$C/workflow-app/pom.xml"
ac2() {
  for i in 1 2 3; do
    sh "$C/scripts/ci/test-order/AC2-webconfig-first.sh" > "$V/sens2-$1-AC2-$i.txt" 2>&1
    echo "$1 run $i exit=$? | $(grep -a 'approvedBatchIsPublished:\|NoSuchFile\|No pending' "$V/sens2-$1-AC2-$i.txt" | head -1 | cut -c1-120) | $(tail -1 "$V/sens2-$1-AC2-$i.txt")"
  done
}
grep -v '<report.dir>' "$V/pom.head.xml" > "$P"; ac2 m2-no-reportdir
sed 's|<argLine>@{argLine} "-Djava.io.tmpdir=${project.build.directory}"</argLine>|<argLine>@{argLine}</argLine>|' "$V/pom.head.xml" > "$P"; ac2 m3-no-tmpdir
cp "$V/pom.head.xml" "$P"
for i in 1 2 3; do
  sh "$C/scripts/ci/test-order/AC2-webconfig-first.sh" > "$V/sens2-head-AC2-$i.txt" 2>&1
  echo "head run $i exit=$? | $(tail -1 "$V/sens2-head-AC2-$i.txt")"
done
git -C "$C" status --short
