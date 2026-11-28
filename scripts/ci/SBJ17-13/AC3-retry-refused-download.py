"""AC3 Maven retries a refused download at least 5 times over at least a minute.

A real refusal, on demand: starts a local server that answers every request with HTTP 429 (Too Many Requests),
points the runner's own mvn at it (a mirror for every repository, an empty local repository, an empty folder),
and asks for a plugin goal, so Maven must download. Maven gets MAVEN_ARGS exactly as each workflow file with a
Maven job sets it at the top (env: MAVEN_ARGS), or none when the file sets none. Passes only when, for every
such workflow, the file Maven asked for most often was asked at least 6 times (the first try and 5 retries),
and the first and last of those tries are at least 60 seconds apart.

Usage: python scripts/ci/SBJ17-13/AC3-retry-refused-download.py
"""
import collections
import http.server
import os
import shutil
import subprocess
import tempfile
import threading
import time

import maven_jobs as mj

MIN_TRIES = 6
MIN_SECONDS = 60
GOAL = "org.apache.maven.plugins:maven-help-plugin:3.5.1:help"
SETTINGS = """<settings><mirrors><mirror><id>refuse-all</id><mirrorOf>*</mirrorOf>
<url>http://127.0.0.1:%d/</url></mirror></mirrors></settings>"""


class Refuse(http.server.BaseHTTPRequestHandler):
    log = []

    def refuse(self):
        Refuse.log.append((time.monotonic(), self.path))
        body = b"Too Many Requests"
        self.send_response(429)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    do_GET = do_HEAD = refuse

    def log_message(self, *args):
        pass


def mvn():
    found = shutil.which("mvn") or shutil.which("mvn.cmd")
    if not found:
        mj.fail(["no mvn on the PATH"])
    return found


def run(maven_args):
    """(tries of the most asked file, seconds from its first to its last try, that file)."""
    Refuse.log = []
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Refuse)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    work = tempfile.mkdtemp(prefix="sbj17-13-ac3-")
    try:
        settings = os.path.join(work, "settings.xml")
        with open(settings, "w", encoding="utf-8") as handle:
            handle.write(SETTINGS % server.server_address[1])
        env = dict(os.environ)
        env.pop("MAVEN_ARGS", None)
        if maven_args:
            env["MAVEN_ARGS"] = maven_args
        command = [mvn(), "-B", "-s", settings, "-Dmaven.repo.local=" + os.path.join(work, "repository"), GOAL]
        started = time.monotonic()
        result = subprocess.run(command, cwd=work, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                universal_newlines=True, timeout=900)
        print("  mvn exited %d after %.0f s" % (result.returncode, time.monotonic() - started))
    finally:
        server.shutdown()
        shutil.rmtree(work, ignore_errors=True)
    if not Refuse.log:
        mj.fail(["Maven made no request to the refusing server; nothing was tested"])
    by_path = collections.defaultdict(list)
    for moment, path in Refuse.log:
        by_path[path].append(moment)
    path, moments = max(by_path.items(), key=lambda item: len(item[1]))
    return len(moments), moments[-1] - moments[0], path


def main():
    version = subprocess.run([mvn(), "-v"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             universal_newlines=True).stdout.splitlines()
    print("Runner's Maven: " + (version[0] if version else "unknown"))
    values = collections.OrderedDict()
    for name, data in mj.maven_workflows():
        value = mj.text((data.get("env") or {}).get("MAVEN_ARGS")) or None
        values.setdefault(value, []).append(name)
    problems = []
    for value, names in values.items():
        print("MAVEN_ARGS %s (%s)" % (repr(value) if value else "not set", ", ".join(names)))
        tries, seconds, path = run(value)
        print("  %s asked %d times over %.0f s" % (path, tries, seconds))
        if tries < MIN_TRIES or seconds < MIN_SECONDS:
            problems.append("%s: a refused download was tried %d times over %.0f s; needs %d times over %d s"
                            % (", ".join(names), tries, seconds, MIN_TRIES, MIN_SECONDS))
    if problems:
        mj.fail(problems)
    print("PASS AC3: every Maven workflow retries a refused download at least 5 times over at least a minute")


if __name__ == "__main__":
    main()
