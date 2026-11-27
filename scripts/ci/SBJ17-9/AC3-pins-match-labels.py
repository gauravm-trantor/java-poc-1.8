"""AC3 Each pinned commit and digest is the one its label pointed to on the day of pinning: no step or image
changes version in this card.

The commits and the digest read on the day of pinning are in pins.py. This check passes only when:
- every uses: line names a step in that table, with exactly its commit and its release in the comment;
- the hbase image is exactly harisekhon/hbase:1.4@<the digest in the table>;
- and, unless --offline: GitHub says each release tag points at its commit (annotated tags followed to the
  commit), and the registry says tag 1.4 is still that digest (docker buildx imagetools inspect).

Usage: python scripts/ci/SBJ17-9/AC3-pins-match-labels.py [--offline] [workflow folder or file] [compose file]
Reads GITHUB_TOKEN, if set, for the GitHub API.
"""
import json
import os
import subprocess
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pins  # noqa: E402


def github(path):
    request = urllib.request.Request("https://api.github.com/" + path,
                                     headers={"Accept": "application/vnd.github+json"})
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        request.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def tag_commit(step, tag):
    target = github("repos/%s/git/ref/tags/%s" % (step, tag))["object"]
    while target["type"] == "tag":
        target = github("repos/%s/git/tags/%s" % (step, target["sha"]))["object"]
    return target["sha"]


def registry_digest(name, tag):
    out = subprocess.run(["docker", "buildx", "imagetools", "inspect", "docker.io/%s:%s" % (name, tag),
                          "--format", "{{json .Manifest}}"], capture_output=True, text=True, check=True).stdout
    return json.loads(out)["digest"]


def main():
    args = [a for a in sys.argv[1:] if a != "--offline"]
    offline = "--offline" in sys.argv[1:]
    problems = []

    files = pins.workflow_files(args[0] if args else None)
    lines = pins.uses_lines(files)
    if not lines:
        problems.append("no uses: lines found")
    for name, number, value in lines:
        where = "%s:%d" % (os.path.relpath(name, pins.ROOT), number)
        match = pins.PINNED.match(value)
        if not match:
            problems.append("%s uses: %s is not pinned" % (where, value))
            continue
        step, sha, release = match.group("step"), match.group("sha"), match.group("release")
        if step not in pins.STEPS:
            problems.append("%s %s was not read on the day of pinning (not in pins.py)" % (where, step))
            continue
        label, want_sha, want_release = pins.STEPS[step]
        if sha != want_sha:
            problems.append("%s %s@%s, but %s pointed to %s" % (where, step, sha, label, want_sha))
        if release != want_release:
            problems.append("%s %s comment says %s, the release at that commit is %s"
                            % (where, step, release, want_release))

    name, tag, digest = pins.IMAGE
    want_image = "%s:%s@%s" % (name, tag, digest)
    image = pins.hbase_image(args[1] if len(args) > 1 else None)
    if image != want_image:
        problems.append("hbase image is %s, expected %s" % (image, want_image))

    if not offline:
        for step, (label, want_sha, release) in sorted(pins.STEPS.items()):
            try:
                got = tag_commit(step, release)
            except Exception as error:  # a network or API failure is a failure of the check, not a pass
                problems.append("could not read %s tag %s from GitHub: %s" % (step, release, error))
                continue
            if got != want_sha:
                problems.append("GitHub says %s %s is %s, pins.py says %s" % (step, release, got, want_sha))
        try:
            got = registry_digest(name, tag)
            if got != digest:
                problems.append("the registry says %s:%s is %s, pins.py says %s" % (name, tag, got, digest))
        except Exception as error:
            problems.append("could not read %s:%s from the registry: %s" % (name, tag, error))

    for problem in problems:
        print("FAIL: " + problem)
    if problems:
        print("AC3 FAIL: %d problem(s)" % len(problems))
        return 1
    print("AC3 PASS: %d uses: lines and the hbase image match the pins read on the day of pinning%s"
          % (len(lines), " (offline)" if offline else ", confirmed with GitHub and the registry"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
