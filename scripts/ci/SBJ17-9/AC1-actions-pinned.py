"""AC1 Every uses: in every file under .github/workflows/ names a full 40-character commit hash, with the release
it stands for in a comment on the same line.

Passes only when every uses: line reads owner/repo[/path]@<40 hex> # v<release>. A moving label (@v7), a short
hash, a hash with no release comment, a docker:// image or a local ./ action each fail.

Usage: python scripts/ci/SBJ17-9/AC1-actions-pinned.py [workflow folder or file]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pins  # noqa: E402


def main():
    files = pins.workflow_files(sys.argv[1] if len(sys.argv) > 1 else None)
    if not files:
        print("FAIL: no workflow files found")
        return 1
    lines = pins.uses_lines(files)
    if not lines:
        print("FAIL: no uses: lines found in %d workflow file(s)" % len(files))
        return 1
    bad = [(f, n, v) for f, n, v in lines if not pins.PINNED.match(v)]
    for name, number, value in bad:
        print("FAIL: %s:%d uses: %s (not a 40-character commit with a # v<release> comment)"
              % (os.path.relpath(name, pins.ROOT), number, value))
    if bad:
        print("AC1 FAIL: %d of %d uses: lines not pinned" % (len(bad), len(lines)))
        return 1
    print("AC1 PASS: %d uses: lines in %d file(s), each a full commit with its release" % (len(lines), len(files)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
