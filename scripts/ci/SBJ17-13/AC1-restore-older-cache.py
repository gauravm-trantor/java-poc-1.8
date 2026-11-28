"""AC1 Each Maven job restores the newest earlier cache when the poms changed.

For every Maven job in every workflow file, passes only when:
- actions/setup-java has no cache: of its own (its cache keys on the pom hash with no fallback);
- an actions/cache/restore step, pinned by commit, with id maven-cache, comes before the job's first run: step;
- it restores ~/.m2/repository under a key that holds the job's name and the hash of every pom;
- it has restore keys that do not hold the pom hash, so a run with changed poms still restores an older cache
  (GitHub takes the newest cache whose key starts with the first restore key that matches), the last being the
  key actions/setup-java saved before this change.

Usage: python scripts/ci/SBJ17-13/AC1-restore-older-cache.py
"""
import maven_jobs as mj

POM_HASH = "hashFiles('**/pom.xml')"
SETUP_JAVA_FALLBACK = "setup-java-${{ runner.os }}-x64-maven-"


def check(name, job_id, job):
    where = "%s job %s" % (name, job_id)
    problems = []
    steps = job.get("steps") or []
    for step in steps:
        if mj.action(step) == "actions/setup-java" and "cache" in (step.get("with") or {}):
            problems.append("%s: actions/setup-java still has cache: %s" % (where, step["with"]["cache"]))
    restore = [i for i, step in enumerate(steps) if mj.action(step) == "actions/cache/restore"]
    if not restore:
        return problems + ["%s: no actions/cache/restore step" % where]
    index = restore[0]
    step = steps[index]
    first_run = next((i for i, s in enumerate(steps) if "run" in s), len(steps))
    if index > first_run:
        problems.append("%s: the restore step comes after the first run: step" % where)
    if not mj.pinned(step):
        problems.append("%s: actions/cache/restore is not pinned by full commit" % where)
    if step.get("id") != "maven-cache":
        problems.append("%s: the restore step's id is not maven-cache" % where)
    with_ = step.get("with") or {}
    if mj.REPOSITORY not in str(with_.get("path", "")).split():
        problems.append("%s: the restore step does not restore %s" % (where, mj.REPOSITORY))
    key = mj.text(with_.get("key"))
    if POM_HASH not in key:
        problems.append("%s: the cache key does not hold %s" % (where, POM_HASH))
    if "github.job" not in key:
        problems.append("%s: the cache key does not hold the job's name (github.job)" % where)
    fallbacks = [mj.text(line) for line in str(with_.get("restore-keys") or "").splitlines() if line.strip()]
    older = [line for line in fallbacks if POM_HASH not in line]
    if not older:
        problems.append("%s: no restore key without the pom hash, so changed poms restore nothing" % where)
    for line in older:
        if line != SETUP_JAVA_FALLBACK and not key.startswith(line):
            problems.append("%s: restore key %r is not a start of the cache key %r" % (where, line, key))
    if not fallbacks or fallbacks[-1] != SETUP_JAVA_FALLBACK:
        problems.append("%s: the last restore key is not %s" % (where, SETUP_JAVA_FALLBACK))
    return problems


def main():
    problems, jobs = [], mj.maven_jobs()
    for name, job_id, job in jobs:
        problems.extend(check(name, job_id, job))
    if problems:
        mj.fail(problems)
    print("PASS AC1: %d Maven jobs restore an older cache when the poms change: %s"
          % (len(jobs), ", ".join("%s/%s" % (n, j) for n, j, _ in jobs)))


if __name__ == "__main__":
    main()
