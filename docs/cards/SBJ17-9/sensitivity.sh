#!/usr/bin/env bash
# SBJ17-9 sensitivity: the checks fail on today's files, pass on a correctly pinned copy, and fail on each broken copy.
# Usage: bash docs/cards/SBJ17-9/sensitivity.sh <scratch folder>   (run from the repository root)
set -u
S=${1:?scratch folder}; mkdir -p "$S"
CI=scripts/ci/SBJ17-9
PY=${PYTHON:-python}
run() { # expect name command...
  local expect=$1 name=$2; shift 2
  "$@" > "$S/out.txt" 2>&1; local code=$?
  local got=pass; [ $code -ne 0 ] && got=fail
  printf '%-4s expected %-4s got %-4s %s: %s\n' "$([ $got = $expect ] && echo OK || echo BAD)" "$expect" "$got" "$name" "$(tail -1 "$S/out.txt")"
}
pin() { sed -e 's#actions/checkout@v7#actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 \# v7.0.1#' \
            -e 's#actions/setup-python@v7#actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0 \# v7.1.0#' \
            -e 's#actions/setup-java@v6#actions/setup-java@d1374f8ac74474200d16ef8ecee22c7ae7a51880 \# v6.3.0#' \
            -e 's#actions/setup-node@v7#actions/setup-node@949feb2413d6458794dcd2491c4babbbce0c15c1 \# v7.1.0#' \
            -e 's#actions/upload-artifact@v7#actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9 \# v7.0.2#' "$1"; }
D=sha256:967b43284d28a6f6b040ed36d70b1d6016488cc9ed934438db8d6b1bfcbb14bb
pin .github/workflows/ci.yml > "$S/good.yml"
sed "s#harisekhon/hbase:1.4\$#harisekhon/hbase:1.4@$D#" docker/local/docker-compose.yml > "$S/good-compose.yml"

echo "== today's files (red) =="
run fail "AC1 today" $PY $CI/AC1-actions-pinned.py
run fail "AC2 today" $PY $CI/AC2-hbase-image-digest.py
run fail "AC3 today" $PY $CI/AC3-pins-match-labels.py --offline
echo "== pinned copy (green) =="
run pass "AC1 pinned" $PY $CI/AC1-actions-pinned.py "$S/good.yml"
run pass "AC2 pinned" $PY $CI/AC2-hbase-image-digest.py "$S/good-compose.yml"
run pass "AC3 pinned" $PY $CI/AC3-pins-match-labels.py --offline "$S/good.yml" "$S/good-compose.yml"
run pass "AC3 pinned, online" $PY $CI/AC3-pins-match-labels.py "$S/good.yml" "$S/good-compose.yml"
echo "== broken copies (each must fail) =="
sed '0,/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1/s//checkout@3d3c42e/' "$S/good.yml" > "$S/m1.yml"
run fail "AC1 short hash" $PY $CI/AC1-actions-pinned.py "$S/m1.yml"
sed '0,/ # v6.3.0/s///' "$S/good.yml" > "$S/m2.yml"
run fail "AC1 no release comment" $PY $CI/AC1-actions-pinned.py "$S/m2.yml"
sed '0,/uses: actions\/setup-node@[^ ]* # v7.1.0/s//uses: docker:\/\/node:22/' "$S/good.yml" > "$S/m3.yml"
run fail "AC1 docker:// step" $PY $CI/AC1-actions-pinned.py "$S/m3.yml"
sed '0,/setup-java@d1374f8ac74474200d16ef8ecee22c7ae7a51880/s//setup-java@d1374f8ac74474200d16ef8ecee22c7ae7a51881/' "$S/good.yml" > "$S/m4.yml"
run pass "AC1 wrong commit (form only)" $PY $CI/AC1-actions-pinned.py "$S/m4.yml"
run fail "AC3 wrong commit" $PY $CI/AC3-pins-match-labels.py --offline "$S/m4.yml" "$S/good-compose.yml"
sed '0,/# v7.0.2/s//# v7.0.1/' "$S/good.yml" > "$S/m5.yml"
run fail "AC3 wrong release in comment" $PY $CI/AC3-pins-match-labels.py --offline "$S/m5.yml" "$S/good-compose.yml"
sed "s#hbase:1.4@$D#hbase@$D#" "$S/good-compose.yml" > "$S/c1.yml"
run fail "AC2 tag dropped" $PY $CI/AC2-hbase-image-digest.py "$S/c1.yml"
sed "s#$D#sha256:967b43284d28a6f6b040ed36d70b1d6016488cc9ed934438db8d6b1bfcbb14b#" "$S/good-compose.yml" > "$S/c2.yml"
run fail "AC2 short digest" $PY $CI/AC2-hbase-image-digest.py "$S/c2.yml"
sed "s#$D#sha256:0000000000000000000000000000000000000000000000000000000000000000#" "$S/good-compose.yml" > "$S/c3.yml"
run pass "AC2 other digest (form only)" $PY $CI/AC2-hbase-image-digest.py "$S/c3.yml"
run fail "AC3 other digest" $PY $CI/AC3-pins-match-labels.py --offline "$S/good.yml" "$S/c3.yml"
