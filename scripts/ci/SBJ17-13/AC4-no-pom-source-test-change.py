"""AC4 No pom, source or test changes (the first half; the second is the maven, ui, Test order and Repeat tests
jobs passing on the same pull request).

Compares the branch with its base (default origin/main) and passes only when every changed or added file is a
workflow file, one of this card's checks under scripts/ci/SBJ17-13/, or a card file under docs/cards/, and no
file was removed.

Usage: python scripts/ci/SBJ17-13/AC4-no-pom-source-test-change.py [base-ref]
"""
import subprocess
import sys

ALLOWED = (".github/workflows/", "scripts/ci/SBJ17-13/", "docs/cards/")


def fail(message):
    print("FAIL: " + message)
    sys.exit(1)


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else "origin/main"
    try:
        out = subprocess.check_output(["git", "diff", "--name-status", "--no-renames", base + "...HEAD"],
                                      universal_newlines=True)
    except subprocess.CalledProcessError:
        fail("cannot compare with %s (fetch it first, or check out with full history)" % base)
    outside, removed = [], []
    for line in out.splitlines():
        status, path = line.split("\t", 1)
        if status.startswith("D"):
            removed.append(path)
        elif not path.startswith(ALLOWED):
            outside.append("%s %s" % (status[0], path))
    if removed:
        fail("files removed: " + ", ".join(removed))
    if outside:
        fail("files changed outside the workflows, scripts/ci/SBJ17-13/ and docs/cards/: " + ", ".join(outside))
    print("PASS AC4: no pom, source or test changed against %s" % base)


if __name__ == "__main__":
    main()
