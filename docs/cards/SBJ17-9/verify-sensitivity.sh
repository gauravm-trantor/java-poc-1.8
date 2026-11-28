#!/usr/bin/env bash
# Verify, SBJ17-9: sensitivity of the card's checks on the real files at the PR head (not the builder's fixtures).
# Usage: bash verify-sensitivity.sh <head clone> <main clone> <work folder>
set -u
H=$1; M=$2; W=$3; rm -rf "$W"; mkdir -p "$W"
CI="$H/scripts/ci/SBJ17-9"; PY=${PYTHON:-python}
run() { local expect=$1 name=$2; shift 2
  "$@" > "$W/out.txt" 2>&1; local code=$?; local got=pass; [ $code -ne 0 ] && got=fail
  printf '%-4s expected %-4s got %-4s %s: %s\n' "$([ $got = $expect ] && echo OK || echo BAD)" "$expect" "$got" "$name" "$(tail -1 "$W/out.txt")"; }
fresh() { rm -rf "$W/$1"; mkdir -p "$W/$1/wf"; cp "$H"/.github/workflows/*.yml "$W/$1/wf/"; cp "$H/docker/local/docker-compose.yml" "$W/$1/compose.yml"; }
all3() { # expect1 expect2 expect3 label dir
  run "$1" "AC1 $4" $PY "$CI/AC1-actions-pinned.py" "$5/wf"
  run "$2" "AC2 $4" $PY "$CI/AC2-hbase-image-digest.py" "$5/compose.yml"
  run "$3" "AC3 $4" $PY "$CI/AC3-pins-match-labels.py" "$5/wf" "$5/compose.yml"; }

echo "== PR head files as they are (online) =="
fresh head; all3 pass pass pass "head" "$W/head"
echo "== main's files, head's checks =="
mkdir -p "$W/main/wf"; cp "$M"/.github/workflows/*.yml "$W/main/wf/"; cp "$M/docker/local/docker-compose.yml" "$W/main/compose.yml"
all3 fail fail fail "main" "$W/main"
echo "== mutants of the real head files =="
fresh m1; sed -i '57s#checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 \# v7.0.1#checkout@v7#' "$W/m1/wf/test-order.yml"
run fail "AC1 last test-order step back to @v7" $PY "$CI/AC1-actions-pinned.py" "$W/m1/wf"
run fail "AC3 last test-order step back to @v7" $PY "$CI/AC3-pins-match-labels.py" "$W/m1/wf" "$W/m1/compose.yml"
fresh m2; sed -i 's#setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0#setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e1#' "$W/m2/wf/ci.yml"
run pass "AC1 skipped job's setup-python one hex off (form only)" $PY "$CI/AC1-actions-pinned.py" "$W/m2/wf"
run fail "AC3 skipped job's setup-python one hex off" $PY "$CI/AC3-pins-match-labels.py" "$W/m2/wf" "$W/m2/compose.yml"
fresh m3; sed -i '0,/# v7.0.1/s//# v7.0.0/' "$W/m3/wf/test-order.yml"
run fail "AC3 real commit, older release named" $PY "$CI/AC3-pins-match-labels.py" "$W/m3/wf" "$W/m3/compose.yml"
fresh m4; printf 'on: push\njobs:\n  x:\n    runs-on: ubuntu-24.04\n    steps:\n      - uses: actions/checkout@v7\n' > "$W/m4/wf/extra.yaml"
run fail "AC1 new .yaml file with a moving label" $PY "$CI/AC1-actions-pinned.py" "$W/m4/wf"
fresh m5; sed -i 's#sha256:967b43284d28a6f6b040ed36d70b1d6016488cc9ed934438db8d6b1bfcbb14bb#sha256:1111111111111111111111111111111111111111111111111111111111111111#' "$W/m5/compose.yml"
run pass "AC2 other digest (form only)" $PY "$CI/AC2-hbase-image-digest.py" "$W/m5/compose.yml"
run fail "AC3 other digest" $PY "$CI/AC3-pins-match-labels.py" "$W/m5/wf" "$W/m5/compose.yml"
fresh m6; sed -i 's#harisekhon/hbase:1.4@#harisekhon/hbase:1.5@#' "$W/m6/compose.yml"
run fail "AC2/AC3 tag changed to 1.5" $PY "$CI/AC3-pins-match-labels.py" "$W/m6/wf" "$W/m6/compose.yml"
