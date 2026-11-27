"""Shared helper for the acceptance checks of card SBJ17-13: finds every Maven job in every workflow file.

A Maven job is a job with an actions/setup-java step. The checks read the workflow files themselves, so they
show what the pipeline is set up to do; the pipeline's own runs show that it does it.
"""
import glob
import os
import re
import sys

import yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
WORKFLOWS = os.path.join(ROOT, ".github", "workflows")
REPOSITORY = "~/.m2/repository"
COMMIT = re.compile(r"^[0-9a-f]{40}$")


def fail(messages):
    for message in messages:
        print("FAIL: " + message)
    sys.exit(1)


def workflow_files():
    return sorted(glob.glob(os.path.join(WORKFLOWS, "*.yml")) + glob.glob(os.path.join(WORKFLOWS, "*.yaml")))


def load(path):
    with open(path, encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    # YAML 1.1 reads the key "on" as the boolean True.
    if True in data and "on" not in data:
        data["on"] = data.pop(True)
    return data


def action(step):
    """The action a step uses, without its version: actions/cache/restore."""
    return str(step.get("uses", "")).split("@")[0]


def pinned(step):
    """True when the step's uses names a full commit."""
    value = str(step.get("uses", ""))
    return "@" in value and bool(COMMIT.match(value.split("@", 1)[1].strip()))


def maven_jobs():
    """(workflow file name, job id, job) for every job with an actions/setup-java step, in every workflow."""
    found = []
    for path in workflow_files():
        data = load(path)
        for job_id, job in (data.get("jobs") or {}).items():
            steps = job.get("steps") or []
            if any(action(step) == "actions/setup-java" for step in steps):
                found.append((os.path.basename(path), job_id, job))
    if not found:
        fail(["no Maven job (a job with actions/setup-java) in .github/workflows/"])
    return found


def maven_workflows():
    """(workflow file name, its data) for every workflow file that has a Maven job."""
    names = sorted({name for name, _, _ in maven_jobs()})
    return [(name, load(os.path.join(WORKFLOWS, name))) for name in names]


def text(value):
    """A workflow value as one string with its whitespace squeezed, for comparing expressions."""
    return " ".join(str(value or "").split())
