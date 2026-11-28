"""AC1 The existing Maven and UI tests are unchanged.

Compares this branch with the point it left main (git merge-base HEAD <ref>), not with main's tip, so a test
another card adds or changes on main later does not count against this card. Every file that existed at that
point under a module's src/test/ folder, or as ui/src/**/*.spec.ts, must be the same on HEAD: not modified,
renamed or deleted. New files beside them are allowed.

Needs full history (actions/checkout with fetch-depth: 0).
Usage: python3 scripts/ci/SBJ17-14/AC1-existing-tests-unchanged.py [ref, default origin/main]
"""
import re
import subprocess
import sys

TEST_FILE = re.compile(r"(^|/)src/test/|^ui/src/.*\.spec\.ts$")


def git(*args):
    return subprocess.run(("git",) + args, capture_output=True, text=True, check=True).stdout


def main():
    ref = sys.argv[1] if len(sys.argv) > 1 else "origin/main"
    try:
        base = git("merge-base", "HEAD", ref).strip()
    except subprocess.CalledProcessError as error:
        print("FAIL AC1: no merge-base of HEAD and %s (%s)" % (ref, error.stderr.strip()))
        sys.exit(1)
    existing = {path for path in git("ls-tree", "-r", "--name-only", base).splitlines() if TEST_FILE.search(path)}
    if not existing:
        print("FAIL AC1: no existing test files found at %s; the pattern is wrong" % base[:12])
        sys.exit(1)
    changed = []
    for line in git("diff", "--name-status", "--no-renames", base, "HEAD").splitlines():
        status, path = line.split("\t", 1)
        if path in existing:
            changed.append("%s %s" % (status, path))
    if changed:
        for entry in changed:
            print("FAIL AC1: existing test changed: " + entry)
        sys.exit(1)
    print("PASS AC1: the %d existing test files are unchanged since %s (merge-base with %s)"
          % (len(existing), base[:12], ref))


if __name__ == "__main__":
    main()
