#!/bin/sh
# Pipeline outcome side by side: main d1284ca against PR head f759a94.
R=gauravm-trantor/java-poc-1.8
for pair in "main 46022251225 46022251178" "head 46054757793 46054757802"; do
  set -- $pair
  echo "=== $1 CI $2, Test order $3"
  for run in $2 $3; do
    gh run view "$run" -R $R --json jobs --jq '.jobs[] | .name + ": " + .conclusion'
    gh run view "$run" -R $R --log 2>/dev/null \
      | grep -E "Tests run: [0-9]+, Failures: [0-9]+, Errors: [0-9]+, Skipped: [0-9]+$|TOTAL: [0-9]+ SUCCESS|PASS AC4|FAIL" \
      | sed -E 's/^([^\t]*)\t[^\t]*\t[0-9TZ:.-]+ /\1: /' | sed -E 's/\x1b\[[0-9;]*[A-Za-z]//g'
  done
done
