#!/usr/bin/env bash
# Sensitivity check for SBJ17-6: each mutant breaks one criterion in a scratch worktree of the PR head,
# then the unchanged acceptance script runs. Expected: the named test fails.
here="$(cd "$(dirname "$0")" && pwd)"
m="$here/mut"
cd "$m" || exit 2
run() { echo "=== $1 (expect $2 to FAIL)"; bash "$here/head/docs/cards/SBJ17-6/acceptance.sh" | grep -E '^(PASS|FAIL)'; git checkout -q -- . ; git clean -qfd -- . ':!docs' >/dev/null 2>&1; }

sed -i 's/Install Node 22.12+; with nvm/Install Node 20.19+; with nvm/' README.md
run "M1 README troubleshooting row back to 20.19" AC1

sed -i 's/nvm use 22`\. nvm applies/nvm use 24.14.0`. nvm applies/' README.md
run "M2 README first nvm hint back to 24.14.0" AC1

sed -i 's/Node 22.12+, Docker/Node 22+, Docker/' README.md
run "M3 README macOS and Linux line loosened to 22+" AC1

sed -i 's/Install Node 22.12 or newer\./Install Node 22 or newer./' setup-local.cmd
run "M4 setup-local.cmd message says 22 only" AC2

sed -i 's/where node >nul 2>nul ||/where node >nul ||/' setup-local.cmd
run "M5 setup-local.cmd check itself changed on the same line" AC2

sed -i 's/$/\r/' setup-local.cmd
run "M6 setup-local.cmd line endings flipped" AC2

sed -i 's/(needs Node 22.12+)/(needs Node 22+)/' latest-ARCHITECTURE.md
run "M7 architecture note loosened" AC2

sed -i '1s/^/<!-- x -->\n/' latest-ARCHITECTURE.md
run "M8 architecture note: a second line changed" AC2

echo "x" >> pom.xml
run "M9 pom.xml changed" AC3

echo "stray" > stray.txt
run "M10 untracked new file at the root" AC3

f="$(git ls-files | grep -m1 '/src/test/')"
echo "// x" >> "$f"
run "M11 an existing test changed ($f)" AC4

sed -i 's/Use Node 22.12 or newer in this terminal\./Use Node 22.12 or newer in this terminal. Node 20.18 also works./' README.md
run "M12 README adds a second, older Node version (not 20.19)" AC1
