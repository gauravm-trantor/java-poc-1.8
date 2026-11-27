"""Shared by the SBJ17-9 checks: where the pipeline's steps and the HBase image are named, and how to read them.

The pins below were read on 2026-11-27 (card file docs/cards/SBJ17-9.md, section Test design): for each step,
the commit its moving label pointed to that day and the release that points at the same commit; for the image,
the digest the tag 1.4 pointed to that day. Criterion AC3 holds the pipeline to exactly these.
"""
import glob
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
WORKFLOWS = os.path.join(ROOT, ".github", "workflows")
COMPOSE = os.path.join(ROOT, "docker", "local", "docker-compose.yml")

# step: (label it was named by, commit the label pointed to, release at that commit)
STEPS = {
    "actions/checkout": ("v7", "3d3c42e5aac5ba805825da76410c181273ba90b1", "v7.0.1"),
    "actions/setup-python": ("v7", "6d4fd22b20465ccc0f7354476588e8df7c9ca0e0", "v7.1.0"),
    "actions/setup-java": ("v6", "d1374f8ac74474200d16ef8ecee22c7ae7a51880", "v6.3.0"),
    "actions/setup-node": ("v7", "949feb2413d6458794dcd2491c4babbbce0c15c1", "v7.1.0"),
    "actions/upload-artifact": ("v7", "cf430e030ddbb5b0abf93d22962f4752f3646cd9", "v7.0.2"),
}
IMAGE = ("harisekhon/hbase", "1.4", "sha256:967b43284d28a6f6b040ed36d70b1d6016488cc9ed934438db8d6b1bfcbb14bb")

USES_LINE = re.compile(r"^\s*(?:-\s+)?uses:\s*(?P<value>.*?)\s*$")
# owner/repo[/path]@<40 hex> # v<release>
PINNED = re.compile(r"^(?P<step>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:/[^@\s]+)?)@(?P<sha>[0-9a-f]{40})"
                    r"\s+#\s*(?P<release>v\d+(?:\.\d+)*)\s*$")
IMAGE_LINE = re.compile(r"^\s*image:\s*(?P<value>\S+)\s*(?:#.*)?$")


def workflow_files(path=None):
    """Every workflow file under the folder (or the one file) given."""
    path = path or WORKFLOWS
    if os.path.isfile(path):
        return [path]
    return sorted(glob.glob(os.path.join(path, "*.yml")) + glob.glob(os.path.join(path, "*.yaml")))


def uses_lines(files):
    """(file, line number, value) for every uses: line, its trailing comment kept."""
    found = []
    for name in files:
        with open(name, encoding="utf-8") as handle:
            for number, line in enumerate(handle, 1):
                match = USES_LINE.match(line)
                if match:
                    found.append((name, number, match.group("value")))
    return found


def hbase_image(compose=None):
    """The image line of the hbase service, read as text so the reference is seen exactly as written."""
    compose = compose or COMPOSE
    service = None
    with open(compose, encoding="utf-8") as handle:
        for line in handle:
            heading = re.match(r"^  (?P<name>[A-Za-z0-9_.-]+):\s*$", line)
            if heading:
                service = heading.group("name")
                continue
            if service == "hbase":
                match = IMAGE_LINE.match(line)
                if match:
                    return match.group("value")
    return None
