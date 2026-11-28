"""AC2 Each Maven job saves its cache even when tests fail.

For every Maven job in every workflow file, passes only when the job's last two steps are actions/cache/save,
pinned by commit, saving ~/.m2/repository:
- one under success(), with the restore step's own key (steps.maven-cache.outputs.cache-primary-key);
- one under failure(), with that key plus -partial- and the run's id and attempt, so a red run saves what it
  downloaded without taking the full key the next green run must save;
and each runs only when the restore step ran (steps.maven-cache.outcome == 'success') and was not an exact hit
(steps.maven-cache.outputs.cache-hit != 'true'), since a key can be saved only once.

Usage: python scripts/ci/SBJ17-13/AC2-save-on-failure.py
"""
import maven_jobs as mj

PRIMARY = "${{ steps.maven-cache.outputs.cache-primary-key }}"
RAN = "steps.maven-cache.outcome == 'success'"
NOT_HIT = "steps.maven-cache.outputs.cache-hit != 'true'"


def check(name, job_id, job):
    where = "%s job %s" % (name, job_id)
    steps = job.get("steps") or []
    last = steps[-2:]
    if len(last) < 2 or any(mj.action(step) != "actions/cache/save" for step in last):
        return ["%s: the last two steps are not actions/cache/save" % where]
    problems = []
    by_condition = {}
    for step in last:
        condition = mj.text(step.get("if"))
        with_ = step.get("with") or {}
        if not mj.pinned(step):
            problems.append("%s: actions/cache/save is not pinned by full commit" % where)
        if mj.REPOSITORY not in str(with_.get("path", "")).split():
            problems.append("%s: a save step does not save %s" % (where, mj.REPOSITORY))
        if RAN not in condition or NOT_HIT not in condition:
            problems.append("%s: save step if: %r lacks %r and %r" % (where, condition, RAN, NOT_HIT))
        for state in ("success()", "failure()"):
            if state in condition:
                by_condition[state] = mj.text(with_.get("key"))
    if by_condition.get("success()") != PRIMARY:
        problems.append("%s: no save under success() with key %s" % (where, PRIMARY))
    partial = by_condition.get("failure()", "")
    if not (partial.startswith(PRIMARY + "-partial-") and "github.run_id" in partial
            and "github.run_attempt" in partial):
        problems.append("%s: no save under failure() with key %s-partial-<run id>-<attempt>" % (where, PRIMARY))
    return problems


def main():
    problems, jobs = [], mj.maven_jobs()
    for name, job_id, job in jobs:
        problems.extend(check(name, job_id, job))
    if problems:
        mj.fail(problems)
    print("PASS AC2: %d Maven jobs save their cache on a green run and a partial one on a red run: %s"
          % (len(jobs), ", ".join("%s/%s" % (n, j) for n, j, _ in jobs)))


if __name__ == "__main__":
    main()
