#!/bin/sh
# Sensitivity check, verifier's own mutants of the real head files.
# Usage: sens.sh <scratch v2 folder>. Each case: copy head, mutate, run AC1..AC3, compare with expected.
V="$1"; W="$V/mut"
export GITHUB_TOKEN=$(gh auth token)
CO=3d3c42e5aac5ba805825da76410c181273ba90b1
pass=0; total=0
run() {  # name, expected "AC1 AC2 AC3" each P or F, sed-expression-or-cmd
  name="$1"; exp="$2"; shift 2
  rm -rf "$W"; mkdir -p "$W"; cp -r "$V/head/.github" "$V/head/docker" "$V/head/scripts" "$W/"
  ( cd "$W" && eval "$@" )
  got=""
  for ac in AC1-actions-pinned AC2-hbase-image-digest AC3-pins-match-labels; do
    if ( cd "$W" && python3 -I "scripts/ci/SBJ17-9/$ac.py" >/dev/null 2>&1 ); then got="$got P"; else got="$got F"; fi
  done
  got="${got# }"; total=$((total+1))
  if [ "$got" = "$exp" ]; then pass=$((pass+1)); r=as-expected; else r=UNEXPECTED; fi
  echo "$r | $name | expected $exp | got $got"
}
run "head unchanged"                         "P P P" true
run "checkout back to @v7 in test-order.yml"   "F P F" "sed -i '57s/@$CO # v7.0.1/@v7/' .github/workflows/test-order.yml"
run "setup-node pin one hex off"             "P P F" "sed -i 's/949feb2413d6458794dcd2491c4babbbce0c15c1/949feb2413d6458794dcd2491c4babbbce0c15c0/' .github/workflows/ci.yml"
run "upload-artifact release comment v7.0.1" "P P F" "sed -i 's/cf430e030ddbb5b0abf93d22962f4752f3646cd9 # v7.0.2/cf430e030ddbb5b0abf93d22962f4752f3646cd9 # v7.0.1/' .github/workflows/ci.yml"
run "short hash on setup-java"               "F P F" "sed -i 's/d1374f8ac74474200d16ef8ecee22c7ae7a51880/d1374f8/' .github/workflows/test-order.yml"
run "release comment removed"                "F P F" "sed -i 's/@$CO # v7.0.1/@$CO/' .github/workflows/ci.yml"
run "new workflow file with moving label"    "F P F" "printf 'on: push\njobs:\n  x:\n    runs-on: ubuntu-24.04\n    steps:\n      - uses: actions/checkout@v7\n' > .github/workflows/extra.yml"
run "image digest dropped (tag only)"        "P F F" "sed -i 's/hbase:1.4@sha256:[0-9a-f]*/hbase:1.4/' docker/local/docker-compose.yml"
run "image digest last char changed"         "P P F" "sed -i 's/bfcbb14bb/bfcbb14ba/' docker/local/docker-compose.yml"
run "image tag 1.4 changed to 1.3"           "P F F" "sed -i 's/hbase:1.4@/hbase:1.3@/' docker/local/docker-compose.yml"
echo "SUMMARY $pass of $total as expected"
rm -rf "$W"
