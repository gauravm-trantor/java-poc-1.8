# Independent probe for SBJ17-9: main's labels vs head's pins, resolved against GitHub.
import glob, json, os, re, subprocess, sys

root = sys.argv[1]
head, main = os.path.join(root, "head"), os.path.join(root, "main")
USES = re.compile(r"^\s*-?\s*uses:\s*(\S+?)@(\S+)(?:\s*#\s*(\S+))?\s*$")

def uses(repo):
    out = []
    for f in sorted(glob.glob(os.path.join(repo, ".github", "workflows", "*.y*ml"))):
        for n, line in enumerate(open(f, encoding="utf-8"), 1):
            m = USES.match(line)
            if m:
                out.append((os.path.basename(f), n, m.group(1), m.group(2), m.group(3)))
            elif "uses:" in line:
                out.append((os.path.basename(f), n, "UNPARSED", line.strip(), None))
    return out

def gh(path):
    return json.loads(subprocess.check_output(["gh", "api", path], text=True))

cache = {}
def resolve(action, tag):
    repo = "/".join(action.split("/")[:2])
    key = (repo, tag)
    if key not in cache:
        ref = gh(f"repos/{repo}/git/ref/tags/{tag}")["object"]
        while ref["type"] == "tag":
            ref = gh(f"repos/{repo}/git/tags/{ref['sha']}")["object"]
        cache[key] = ref["sha"]
    return cache[key]

h, m = uses(head), uses(main)
print(f"main: {len(m)} uses lines; head: {len(h)} uses lines")
main_labels = {}
for f, n, a, ref, c in m:
    main_labels.setdefault((f, a), set()).add(ref)
bad = 0
for f, n, a, ref, c in h:
    ok_form = bool(re.fullmatch(r"[0-9a-f]{40}", ref)) and bool(c) and c.startswith("v")
    res = resolve(a, c) if c else None
    match = res == ref
    old = main_labels.get((f, a), {"(not on main)"})
    same_label = c in old or any(c.startswith(o + ".") or c == o for o in old)
    flag = "OK" if ok_form and match and same_label else "FINDING"
    bad += flag != "OK"
    print(f"{flag} {f}:{n} {a} pin={ref[:12]} comment={c} tag->{(res or '')[:12]} main_label={sorted(old)}")
print("RESULT", "all pins resolve and keep main's labels" if not bad else f"{bad} findings")
