"""AC3 UI tests in headless Chrome on Node 20.19+, fails on any failure.

Passes when one job of .github/workflows/ci.yml sets up Node 20.19 or newer and runs the UI tests in ui/ once,
headless in Chrome, with nothing that hides a failure. The pipeline run shows the job passing; the sensitivity
check in the card file (a throwaway branch with one new failing spec) shows it failing.
"""
import re

import workflow_file as wf


def node_ok(version):
    """'20' and '20.x' resolve to the newest 20 release, which is past 20.19. Older pins are refused."""
    text = str(version).strip().lstrip("v")
    if text in ("lts/*", "latest", "node"):
        return True
    match = re.match(r"^(\d+)(?:\.(\d+|x))?", text)
    if not match:
        return False
    major = int(match.group(1))
    minor = match.group(2)
    if major > 20:
        return True
    if major < 20:
        return False
    return minor in (None, "x") or int(minor) >= 19


def main():
    found = []
    for name, job in wf.jobs(wf.load()).items():
        commands = [line for line in wf.run_lines(job) if "ng test" in line or "npm test" in line]
        if not commands:
            continue
        nodes = [str((s.get("with") or {}).get("node-version")) for s in wf.uses(job, "actions/setup-node")]
        if not nodes or not all(node_ok(v) for v in nodes):
            wf.fail("job %s runs the UI tests but its Node (%s) is not 20.19 or newer" % (name, nodes or "none"))
        wf.no_ignored_failure(name, job)
        for command in commands:
            if "--browsers=ChromeHeadless" not in command:
                wf.fail("job %s does not run the UI tests in headless Chrome: %s" % (name, command))
            if "--watch=false" not in command:
                wf.fail("job %s does not run the UI tests once (--watch=false): %s" % (name, command))
            if "|| true" in command or "||true" in command:
                wf.fail("job %s hides UI test failures" % name)
        found.append(name)
    if not found:
        wf.fail("no job runs the UI tests")
    print("PASS AC3: job %s runs the UI tests once in headless Chrome on Node 20.19 or newer" % ", ".join(found))


if __name__ == "__main__":
    main()
