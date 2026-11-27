"""AC1 runs on each pull request to main and push to main.

Passes when .github/workflows/ci.yml is triggered by pull_request and by push, each limited to (or including) main.
"""
import workflow_file as wf


def branches_of(trigger, name):
    if trigger is None:
        return None  # "pull_request:" with no settings means every branch, main included
    if not isinstance(trigger, dict):
        wf.fail("%s has an unexpected form" % name)
    if "branches-ignore" in trigger and "main" in (trigger["branches-ignore"] or []):
        wf.fail("%s ignores main" % name)
    return trigger.get("branches")


def main():
    on = wf.load().get("on")
    if isinstance(on, str):
        on = {on: None}
    elif isinstance(on, list):
        on = {event: None for event in on}
    if not isinstance(on, dict):
        wf.fail("the pipeline has no triggers")
    for event in ("pull_request", "push"):
        if event not in on:
            wf.fail("the pipeline does not run on %s" % event)
        branches = branches_of(on[event], event)
        if branches is not None and "main" not in branches:
            wf.fail("%s does not include main (branches: %s)" % (event, branches))
    print("PASS AC1: the pipeline runs on each pull request to main and each push to main")


if __name__ == "__main__":
    main()
