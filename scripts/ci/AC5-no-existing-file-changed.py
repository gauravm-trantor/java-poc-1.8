"""AC5 no existing source, pom or test changes.

Compares the branch with its base (default origin/main) and passes only when no file that exists on the base
was changed, removed or renamed, apart from this card's own notes under docs/cards/, and every added file is
the pipeline, these checks or the card's notes.

Usage: python scripts/ci/AC5-no-existing-file-changed.py [base-ref]
"""
import subprocess
import sys

ALLOWED_NEW = (".github/workflows/", "scripts/ci/", "docs/cards/")
ALLOWED_CHANGED = ("docs/cards/",)


def fail(message):
    print("FAIL: " + message)
    sys.exit(1)


def changes(base):
    try:
        out = subprocess.check_output(["git", "diff", "--name-status", "--no-renames", base + "...HEAD"],
                                      universal_newlines=True)
    except subprocess.CalledProcessError:
        fail("cannot compare with %s (fetch it first, or check out with full history)" % base)
    for line in out.splitlines():
        status, path = line.split("\t", 1)
        yield status[0], path


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else "origin/main"
    changed, unexpected = [], []
    for status, path in changes(base):
        if status == "A":
            if not path.startswith(ALLOWED_NEW):
                unexpected.append(path)
        elif not path.startswith(ALLOWED_CHANGED):
            changed.append("%s %s" % (status, path))
    if changed:
        fail("existing files changed: " + ", ".join(changed))
    if unexpected:
        fail("files added outside the pipeline, scripts/ci/ and docs/cards/: " + ", ".join(unexpected))
    print("PASS AC5: no existing file changed against %s" % base)


if __name__ == "__main__":
    main()
