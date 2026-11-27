#!/usr/bin/env bash
# Acceptance tests for card SBJ17-6 (README and setup notes name Node 22.12 or newer).
# Run from anywhere inside the repository: bash docs/cards/SBJ17-6/acceptance.sh
# BASE overrides the commit the change is compared with (default: merge base with origin/main).
# Each test finds its line by text, not by line number. Exit 1 if any test fails.
set -u
cd "$(git rev-parse --show-toplevel)" || exit 2
BASE="${BASE:-$(git merge-base origin/main HEAD)}"
failures=0

# line_has FILE ANCHOR EXPECTED: the first line holding ANCHOR also holds EXPECTED.
line_has() {
  local line
  line="$(grep -F -m1 -- "$2" "$1" || true)"
  if [ -z "$line" ]; then echo "  missing line with: $2 ($1)"; return 1; fi
  case "$line" in *"$3"*) return 0 ;; esac
  echo "  $1: line with '$2' does not hold '$3'"; return 1
}

no_text() {
  if grep -n -F -- "$2" "$1"; then echo "  $1 still holds '$2'"; return 1; fi
  return 0
}

one_line_changed() {
  local stat
  stat="$(git diff --numstat "$BASE" -- "$1" | awk '{print $1" "$2}')"
  if [ "$stat" = "1 1" ]; then return 0; fi
  echo "  $1: expected one line changed against $BASE, got '${stat:-no change}'"; return 1
}

report() {
  if [ "$2" -eq 0 ]; then echo "PASS $1"; else echo "FAIL $1"; failures=$((failures + 1)); fi
}

AC1_readme_names_node_22_12() {
  local rc=0 f=README.md
  no_text "$f" "20.19" || rc=1
  line_has "$f" "**Node.js**" "**22.12 or newer**" || rc=1
  line_has "$f" "node -v " "v22.12 or newer" || rc=1
  line_has "$f" "several Node versions (nvm)" "nvm use 22" || rc=1
  line_has "$f" "Install the same tools" "Node 22.12+" || rc=1
  line_has "$f" "in this terminal." "Use Node 22.12 or newer" || rc=1
  line_has "$f" "Node is too old" "Install Node 22.12+" || rc=1
  line_has "$f" "Node is too old" "nvm use 22" || rc=1
  return $rc
}

AC2_script_and_architecture_say_22_12() {
  local rc=0
  no_text setup-local.cmd "20.19" || rc=1
  no_text latest-ARCHITECTURE.md "20.19" || rc=1
  line_has setup-local.cmd "Node.js was not found on PATH" "Install Node 22.12 or newer." || rc=1
  line_has setup-local.cmd "Node.js was not found on PATH" "where node >nul 2>nul ||" || rc=1
  line_has latest-ARCHITECTURE.md "| Angular | 20 |" "(needs Node 22.12+)" || rc=1
  one_line_changed setup-local.cmd || rc=1
  one_line_changed latest-ARCHITECTURE.md || rc=1
  return $rc
}

AC3_only_three_files_and_card_docs_change() {
  local rc=0 path
  while IFS= read -r path; do
    [ -z "$path" ] && continue
    case "$path" in
      README.md|setup-local.cmd|latest-ARCHITECTURE.md|docs/cards/*) ;;
      *) echo "  changed outside the allowed files: $path"; rc=1 ;;
    esac
  done < <( { git diff --name-only "$BASE"; git ls-files --others --exclude-standard; } | sort -u )
  return $rc
}

# AC4's other half, that the pipeline passes on the pull request, is read from the pipeline run itself.
AC4_existing_tests_unchanged() {
  local changed
  changed="$(git diff --name-only "$BASE" | grep -E '(^|/)src/test/|\.spec\.ts$|(^|/)test/' || true)"
  if [ -n "$changed" ]; then echo "  test files changed:"; echo "$changed" | sed 's/^/    /'; return 1; fi
  return 0
}

echo "Comparing with $BASE"
for t in AC1_readme_names_node_22_12 AC2_script_and_architecture_say_22_12 AC3_only_three_files_and_card_docs_change AC4_existing_tests_unchanged; do
  "$t"; report "$t" $?
done
[ "$failures" -eq 0 ]
