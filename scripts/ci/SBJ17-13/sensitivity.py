"""Sensitivity check of card SBJ17-13's acceptance checks (not an acceptance check itself).

Before the build the checks fail, which shows they notice today's pipeline. This shows the other half: that
they can pass, and that each guard they test is one they would miss. It works on throwaway copies only:
- AC1, AC2: copies the repository, applies the Plan's design to every Maven job (the "built" copy), expects
  PASS; then breaks one guard at a time in one job and expects FAIL.
- AC3: runs the check's own refusing server and mvn with the Plan's MAVEN_ARGS (expects PASS) and with too few
  retries (expects FAIL).
- AC4: clones the repository, changes one pom and commits, expects FAIL.

Usage: python scripts/ci/SBJ17-13/sensitivity.py [--skip-ac3]
"""
import copy
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
PIN = "0" * 40  # any 40-hex commit; the checks test the shape, not the action
KEY = "maven-${{ runner.os }}-${{ github.job }}-${{ hashFiles('**/pom.xml') }}"
FALLBACK = "setup-java-${{ runner.os }}-x64-maven-"
RESTORE = {
    "name": "Restore the Maven repository", "id": "maven-cache", "uses": "actions/cache/restore@" + PIN,
    "with": {"path": "~/.m2/repository", "key": KEY,
             "restore-keys": "\n".join([KEY + "-partial-", "maven-${{ runner.os }}-${{ github.job }}-",
                                        "maven-${{ runner.os }}-", FALLBACK]) + "\n"}}
GUARD = "steps.maven-cache.outcome == 'success' && steps.maven-cache.outputs.cache-hit != 'true'"
PRIMARY = "${{ steps.maven-cache.outputs.cache-primary-key }}"
SAVE_OK = {"name": "Save the Maven repository", "if": "success() && " + GUARD, "uses": "actions/cache/save@" + PIN,
           "with": {"path": "~/.m2/repository", "key": PRIMARY}}
SAVE_FAIL = {"name": "Save the Maven repository, run failed", "if": "failure() && " + GUARD,
             "uses": "actions/cache/save@" + PIN,
             "with": {"path": "~/.m2/repository",
                      "key": PRIMARY + "-partial-${{ github.run_id }}-${{ github.run_attempt }}"}}
MAVEN_ARGS = "-Daether.connector.http.retryHandler.count=6 -Daether.connector.http.retryHandler.interval=10000"
TOO_FEW = "-Daether.connector.http.retryHandler.count=4 -Daether.connector.http.retryHandler.interval=10000"
AC1, AC2 = "AC1-restore-older-cache.py", "AC2-save-on-failure.py"


def load(path):
    with open(path, encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if True in data and "on" not in data:
        data["on"] = data.pop(True)
    return data


def is_(step, action):
    return str(step.get("uses", "")).split("@")[0] == action


def restore(steps):
    return next(step for step in steps if is_(step, "actions/cache/restore"))


def built_copy(work, mutate=None):
    """A copy of the workflows and checks with the design applied; mutate(steps) breaks ci.yml's maven job."""
    if os.path.exists(work):
        shutil.rmtree(work)
    shutil.copytree(os.path.join(ROOT, ".github"), os.path.join(work, ".github"))
    shutil.copytree(HERE, os.path.join(work, "scripts", "ci", "SBJ17-13"))
    folder = os.path.join(work, ".github", "workflows")
    for name in sorted(os.listdir(folder)):
        path = os.path.join(folder, name)
        data, changed = load(path), False
        for job_id, job in (data.get("jobs") or {}).items():
            steps = job.get("steps") or []
            at = [i for i, step in enumerate(steps) if is_(step, "actions/setup-java")]
            if not at:
                continue
            changed = True
            (steps[at[0]].get("with") or {}).pop("cache", None)
            steps.insert(at[0] + 1, copy.deepcopy(RESTORE))
            steps.extend([copy.deepcopy(SAVE_OK), copy.deepcopy(SAVE_FAIL)])
            if mutate and name == "ci.yml" and job_id == "maven":
                mutate(steps)
        if changed:
            data.setdefault("env", {})["MAVEN_ARGS"] = MAVEN_ARGS
            with open(path, "w", encoding="utf-8") as handle:
                yaml.safe_dump(data, handle, sort_keys=False)


def run_check(work, check):
    result = subprocess.run([sys.executable, os.path.join(work, "scripts", "ci", "SBJ17-13", check)],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    first = (result.stdout.strip().splitlines() or [""])[0]
    return ("PASS" if result.returncode == 0 else "FAIL"), first


def set_cache(steps):
    next(s for s in steps if is_(s, "actions/setup-java")).setdefault("with", {})["cache"] = "maven"


CASES = [
    ("built copy", None, AC1, "PASS"),
    ("built copy", None, AC2, "PASS"),
    ("setup-java keeps cache: maven", set_cache, AC1, "FAIL"),
    ("no restore keys", lambda s: restore(s)["with"].pop("restore-keys"), AC1, "FAIL"),
    ("every restore key holds the pom hash",
     lambda s: restore(s)["with"].update({"restore-keys": KEY + "-partial-\n"}), AC1, "FAIL"),
    ("setup-java's old key not the last fallback",
     lambda s: restore(s)["with"].update({"restore-keys": KEY + "-partial-\nmaven-${{ runner.os }}-\n"}), AC1, "FAIL"),
    ("key without the job's name",
     lambda s: restore(s)["with"].update(key="maven-${{ hashFiles('**/pom.xml') }}"), AC1, "FAIL"),
    ("restore by label, not commit", lambda s: restore(s).update(uses="actions/cache/restore@v5"), AC1, "FAIL"),
    ("restore after the first run step", lambda s: s.insert(len(s) - 2, s.pop(s.index(restore(s)))), AC1, "FAIL"),
    ("no save under failure()", lambda s: s.pop(), AC2, "FAIL"),
    ("failure save takes the full key", lambda s: s[-1]["with"].update(key=PRIMARY), AC2, "FAIL"),
    ("failure save without the restore guard", lambda s: s[-1].update({"if": "failure()"}), AC2, "FAIL"),
    ("a step after the saves", lambda s: s.append({"name": "late", "run": "true"}), AC2, "FAIL"),
    ("success save by label", lambda s: s[-2].update(uses="actions/cache/save@v5"), AC2, "FAIL"),
]


def ac4_case(work):
    clone = os.path.join(work, "clone")
    subprocess.check_call(["git", "clone", "-q", ROOT, clone])
    base = subprocess.check_output(["git", "-C", clone, "rev-parse", "HEAD"], universal_newlines=True).strip()
    with open(os.path.join(clone, "pom.xml"), "a", encoding="utf-8") as handle:
        handle.write("<!-- sensitivity -->\n")
    subprocess.check_call(["git", "-C", clone, "-c", "user.name=s", "-c", "user.email=s@s", "commit", "-qam", "pom"])
    result = subprocess.run([sys.executable, os.path.join(clone, "scripts", "ci", "SBJ17-13",
                                                         "AC4-no-pom-source-test-change.py"), base],
                            cwd=clone, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    return ("PASS" if result.returncode == 0 else "FAIL"), (result.stdout.strip().splitlines() or [""])[0]


def ac3_cases():
    spec = importlib.util.spec_from_file_location("ac3", os.path.join(HERE, "AC3-retry-refused-download.py"))
    sys.path.insert(0, HERE)
    ac3 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ac3)
    out = []
    for label, args, want in [("design's MAVEN_ARGS", MAVEN_ARGS, "PASS"), ("4 retries only", TOO_FEW, "FAIL")]:
        tries, seconds, path = ac3.run(args)
        got = "PASS" if tries >= ac3.MIN_TRIES and seconds >= ac3.MIN_SECONDS else "FAIL"
        out.append(("AC3", label, want, got, "%d tries over %.0f s of %s" % (tries, seconds, path)))
    return out


def main():
    results = []
    work = tempfile.mkdtemp(prefix="sbj17-13-sensitivity-")
    try:
        for label, mutate, check, want in CASES:
            built_copy(os.path.join(work, "copy"), mutate)
            got, line = run_check(os.path.join(work, "copy"), check)
            results.append((check.split("-")[0], label, want, got, line))
        got, line = ac4_case(work)
        results.append(("AC4", "a pom changed", "FAIL", got, line))
    finally:
        shutil.rmtree(work, ignore_errors=True)
    if "--skip-ac3" not in sys.argv:
        results.extend(ac3_cases())
    misses = 0
    for check, label, want, got, line in results:
        misses += want != got
        print("%-4s %s, %s: want %s, got %s | %s" % ("ok" if want == got else "MISS", check, label, want, got, line))
    print("sensitivity: %d of %d cases as expected" % (len(results) - misses, len(results)))
    sys.exit(1 if misses else 0)


if __name__ == "__main__":
    main()
