"""Side-by-side run for SBJ17-11, Verify: main against the pull request's head, through the real REST API.

Usage: python -I sbs.py <old-clone> <new-clone> <inputs-dir> <out-dir> <env-names comma separated> [<scenario names>]
Each side runs LocalDebugServer (real HBase in docker/local, Spark as a child JVM) with a fresh H2 workflow database
and its own report folder. Business dates are unique per side and environment; the date is masked before comparing.
"""
import json, os, shutil, subprocess, sys, time, urllib.request, urllib.error

ENVS = {
    "default": [],
    "latin1": ["-Dfile.encoding=ISO-8859-1"],
    "ar-EG": ["-Duser.language=ar", "-Duser.country=EG"],
    "hi-IN": ["-Duser.language=hi", "-Duser.country=IN"],
    "tz-kiritimati": ["-Duser.timezone=Pacific/Kiritimati"],
}

# (name, input file or None, action after the run settles: approve|reject|none, fast: approve the instant WAITING_APPROVAL shows)
SCENARIOS = {
    "s15-approve": ("sales-20261115.csv", "approve", False),
    "s13-approve": ("sales-20261113.csv", "approve", False),
    "s15-reject": ("sales-20261115.csv", "reject", False),
    "s15-fast-approve": ("sales-20261115.csv", "approve", True),
    "bad": ("sales-bad.csv", "none", False),
    "empty": ("empty.csv", "none", False),
    "header-only": ("header-only.csv", "none", False),
    "edge-values": ("edge-values.csv", "approve", False),
    "missing-file": ("does-not-exist.csv", "none", False),
}


def http(method, url, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def start_server(clone, port, flags, workdir):
    wa = os.path.join(clone, "workflow-app", "target")
    cp = open(os.path.join(wa, "local-classpath.txt")).read().strip()
    cp = os.pathsep.join([os.path.join(wa, "test-classes"), os.path.join(wa, "classes"), cp])
    db = (workdir + "/activiti").replace("\\", "/")
    cmd = ["java", "-Dserver.port=%d" % port, "-Dreport.dir=" + os.path.join(workdir, "reports"),
           "-Dactiviti.jdbc.url=jdbc:h2:file:%s;DB_CLOSE_DELAY=-1" % db] + flags + [
        "-cp", cp, "com.example.salesbatch.workflow.LocalDebugServer"]
    log = open(os.path.join(workdir, "server.log"), "w", encoding="utf-8", errors="replace")
    p = subprocess.Popen(cmd, cwd=clone, stdout=log, stderr=subprocess.STDOUT)
    for _ in range(240):
        time.sleep(0.5)
        try:
            urllib.request.urlopen("http://localhost:%d/batches/none" % port, timeout=2)
        except urllib.error.HTTPError:
            return p
        except Exception:
            if p.poll() is not None:
                raise RuntimeError("server exited, see " + log.name)
    raise RuntimeError("server did not start")


def run_scenario(base, inputs, name, date, workdir):
    fname, action, fast = SCENARIOS[name]
    path = os.path.join(inputs, fname).replace("\\", "/")
    res = {"scenario": name}
    code, body = http("POST", base + "/batches", {"csvPath": path, "businessDate": date})
    res["start"] = code
    if code != 202:
        res["start_body"] = body
        return res
    pid = json.loads(body)["processInstanceId"]
    seen, last, t0 = [], None, time.time()
    approve_code = approve_body = None
    while time.time() - t0 < 300:
        c, b = http("GET", base + "/batches/" + pid)
        st = json.loads(b) if c == 200 else {"status": "HTTP%d" % c}
        s = st.get("status")
        if s != last:
            seen.append(s)
            last = s
        if s == "WAITING_APPROVAL" and fast and approve_code is None:
            approve_code, approve_body = http("POST", base + "/batches/%s/approve?approved=true&approver=alice" % pid)
            continue
        if s in ("WAITING_APPROVAL", "FAILED", "COMPLETED", "REJECTED"):
            if s == "WAITING_APPROVAL" and action in ("approve", "reject") and approve_code is None:
                approve_code, approve_body = http("POST", base + "/batches/%s/approve?approved=%s&approver=alice"
                                                  % (pid, "true" if action == "approve" else "false"))
                continue
            if s != "WAITING_APPROVAL" or action == "none":
                res["final"] = st
                break
        time.sleep(0.02)
    res["statuses"] = seen
    res["approve"] = approve_code
    if approve_body is not None:
        try:
            res["approve_status"] = json.loads(approve_body).get("status")
        except Exception:
            res["approve_body"] = approve_body[:200]
    if "final" in res:
        res["final"].pop("processInstanceId", None)
        res["final"] = json.loads(json.dumps(res["final"]).replace(date, "<DATE>"))
    rep = os.path.join(workdir, "reports", "report-%s.csv" % date)
    if os.path.exists(rep):
        res["report"] = open(rep, "rb").read().replace(date.encode(), b"<DATE>").decode("latin-1")
    # data endpoints
    for kind in ("raw", "agg"):
        c, b = http("GET", base + "/data/%s?date=%s" % (kind, date))
        res[kind] = (c, b.replace(date, "<DATE>"))
    return res


def api_probes(base):
    out = {}
    out["status-unknown"] = http("GET", base + "/batches/no-such-run")
    out["approve-unknown"] = http("POST", base + "/batches/no-such-run/approve?approved=true&approver=a")
    out["start-bad-date"] = http("POST", base + "/batches", {"csvPath": "x.csv", "businessDate": "2026-11-15"})
    out["start-null-date"] = http("POST", base + "/batches", {"csvPath": "x.csv"})
    out["start-empty-body"] = http("POST", base + "/batches", {})
    out["raw-bad-date"] = http("GET", base + "/data/raw?date=abc")
    return out


def main():
    old, new, inputs, out, envs = sys.argv[1:6]
    names = sys.argv[6].split(",") if len(sys.argv) > 6 else list(SCENARIOS)
    os.makedirs(out, exist_ok=True)
    results = {}
    day = int(time.strftime("%j"))
    for ei, env in enumerate(envs.split(",")):
        for si, (side, clone) in enumerate((("old", old), ("new", new))):
            work = os.path.join(out, "%s-%s" % (side, env))
            shutil.rmtree(work, ignore_errors=True)
            os.makedirs(work)
            port = 18100 + si
            p = start_server(clone, port, ENVS[env], work)
            base = "http://localhost:%d" % port
            try:
                r = {"probes": api_probes(base)}
                for ni, n in enumerate(names):
                    # unique date per side, env, scenario: 2091-2092, month from env, day from scenario
                    date = "%s%d%02d%02d" % (os.environ.get("SBS_YEAR", "207"), 1 + si, 1 + ei, 1 + ni)
                    date = "%s" % date
                    r[n] = run_scenario(base, inputs, n, date, work)
                    r[n].pop("date", None)
                results.setdefault(env, {})[side] = r
            finally:
                p.terminate()
                try:
                    p.wait(20)
                except Exception:
                    p.kill()
            json.dump(results, open(os.path.join(out, "detail.json"), "w"), indent=1)
    # compare
    lines, total, differ = [], 0, 0
    for env, sides in results.items():
        o, n = sides["old"], sides["new"]
        for key in o:
            total += 1
            if o[key] != n.get(key):
                differ += 1
                if isinstance(o[key], dict):
                    fields = [f for f in set(o[key]) | set(n[key]) if o[key].get(f) != n[key].get(f)]
                    lines.append("DIFF %s %s fields %s: old %s | new %s" % (env, key, fields,
                                 json.dumps({f: o[key].get(f) for f in fields})[:400],
                                 json.dumps({f: n[key].get(f) for f in fields})[:400]))
                else:
                    lines.append("DIFF %s %s" % (env, key))
            else:
                lines.append("same %s %s" % (env, key))
    summary = "cases %d, differ %d\n" % (total, differ) + "\n".join(lines) + "\n"
    open(os.path.join(out, "summary.txt"), "w").write(summary)
    print(summary)


if __name__ == "__main__":
    main()
