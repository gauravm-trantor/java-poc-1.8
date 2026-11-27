"""Shared helper for the acceptance checks of card SBJ17-2: loads the pipeline file .github/workflows/ci.yml.

The checks read the workflow file itself, so they show what the pipeline is set up to do.
The pipeline's own run shows that it does it.
"""
import os
import sys

import yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
WORKFLOW = os.path.join(ROOT, ".github", "workflows", "ci.yml")


def fail(message):
    print("FAIL: " + message)
    sys.exit(1)


def load():
    if not os.path.isfile(WORKFLOW):
        fail("no pipeline file at .github/workflows/ci.yml")
    with open(WORKFLOW, encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        fail("the pipeline file is empty or not a mapping")
    # YAML 1.1 reads the key "on" as the boolean True.
    if True in data and "on" not in data:
        data["on"] = data.pop(True)
    return data


def jobs(data):
    found = data.get("jobs") or {}
    if not isinstance(found, dict):
        fail("jobs is not a mapping")
    return found


def run_lines(job):
    """Every shell line the job runs, with line continuations joined."""
    lines = []
    for step in job.get("steps") or []:
        script = step.get("run")
        if script:
            lines.extend(script.replace("\\\n", " ").splitlines())
    return [" ".join(line.split()) for line in lines]


def uses(job, action):
    """The steps of a job that use the named action (any version)."""
    return [s for s in job.get("steps") or [] if str(s.get("uses", "")).split("@")[0] == action]


def no_ignored_failure(name, job):
    """A job that hides its own failure cannot fail on a failed test."""
    if job.get("continue-on-error"):
        fail("job %s has continue-on-error" % name)
    for step in job.get("steps") or []:
        if step.get("continue-on-error"):
            fail("a step in job %s has continue-on-error: %s" % (name, step.get("name") or step.get("run")))
