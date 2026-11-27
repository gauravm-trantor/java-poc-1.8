"""AC2 mvn -B clean test on JDK 8, fails on any failed test.

Passes when one job of .github/workflows/ci.yml sets up Temurin JDK 8 and runs mvn -B clean test from the
repository root, with nothing that hides a failed test. The pipeline run shows the job passing; the sensitivity
check in the card file (a throwaway branch with one new failing test) shows it failing.
"""
import workflow_file as wf

HIDING = ("-DskipTests", "-Dmaven.test.skip", "-Dmaven.test.failure.ignore", "-Dmaven.test.error.ignore",
          "-fae", "--fail-at-end", "-fn", "--fail-never", "|| true", "||true")


def is_jdk8(job):
    for step in wf.uses(job, "actions/setup-java"):
        settings = step.get("with") or {}
        if str(settings.get("java-version")) in ("8", "1.8") and settings.get("distribution") == "temurin":
            return True
    return False


def main():
    found = []
    for name, job in wf.jobs(wf.load()).items():
        commands = [line for line in wf.run_lines(job) if "mvn" in line.split() and "test" in line.split()]
        if not commands:
            continue
        if not is_jdk8(job):
            wf.fail("job %s runs Maven tests but does not set up Temurin JDK 8" % name)
        wf.no_ignored_failure(name, job)
        for command in commands:
            if "mvn -B clean test" not in command:
                wf.fail("job %s runs '%s', not mvn -B clean test" % (name, command))
            for flag in HIDING:
                if flag in command:
                    wf.fail("job %s hides test failures with %s" % (name, flag))
        found.append(name)
    if not found:
        wf.fail("no job runs mvn -B clean test")
    print("PASS AC2: job %s runs mvn -B clean test on Temurin JDK 8 and fails on a failed test" % ", ".join(found))


if __name__ == "__main__":
    main()
