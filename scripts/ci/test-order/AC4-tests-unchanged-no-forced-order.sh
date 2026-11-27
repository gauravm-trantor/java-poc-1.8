#!/bin/sh
# AC4 The existing tests are unchanged, and the pipeline no longer forces a test order.
# That all existing tests pass is shown by the AC1 runs and the main CI job.
# Usage: AC4-tests-unchanged-no-forced-order.sh [base ref, default origin/main]
. "$(dirname -- "$0")/common.sh"

base="${1:-origin/main}"
fail=0

changed=$(git -C "$ROOT" diff --name-only --diff-filter=MDRT "$base"...HEAD -- '*/src/test/*')
if [ -n "$changed" ]; then
  echo "AC4 FAILED: existing test files changed or removed since $base:"; echo "$changed"; fail=1
else
  echo "AC4: no existing test file changed since $base"
fi

forced=""
for f in "$ROOT"/.github/workflows/*.yml "$ROOT"/.github/workflows/*.yaml; do
  [ -f "$f" ] || continue
  case "$(basename "$f")" in test-order.yml) continue ;; esac
  if grep -n "surefire.runOrder" "$f" >/dev/null; then forced="$forced $(basename "$f")"; fi
done
if [ -n "$forced" ]; then
  echo "AC4 FAILED: the pipeline still forces a test order in:$forced"; fail=1
else
  echo "AC4: no pipeline file forces a test order"
fi

[ "$fail" -eq 0 ] && echo "AC4 passed"
exit "$fail"
