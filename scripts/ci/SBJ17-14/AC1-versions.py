"""AC1 Every module builds on JDK 8 against Spark 3.5.8, Scala 2.12.18, Hadoop 3.4.2, HBase 2.6.4 and
ZooKeeper 3.9.3 (open-source Apache artifacts).

Runs `mvn -B compile dependency:list` at the root (compile, so the reactor resolves `common` for the other
modules), then reads each module's resolved list, every scope. Passes only when:
- the five named artifacts are resolved at their versions (spark-core_2.12, scala-library, hadoop-client,
  hbase-client, zookeeper);
- no artifact of the groups org.apache.spark, org.scala-lang, org.apache.hadoop, org.apache.hbase or
  org.apache.zookeeper is at any other version (one stray Hadoop 3.3 jar beside 3.4.2 is a failure);
- no artifact is built for Scala 2.11 (artifactId ending in _2.11);
- the build still compiles for Java 8: the root pom's java.version is 1.8.
The modules compiling under `mvn` on the pipeline's JDK 8 is the "builds on JDK 8" part; the maven and ui
jobs passing is the rest of AC1.

Usage: python3 scripts/ci/SBJ17-14/AC1-versions.py [--no-build]
  --no-build  read the lists a previous run left in <module>/target/sbj17-14-deps.txt
"""
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
MODULES = ("common", "spark-job", "workflow-app")
LIST_FILE = os.path.join("target", "sbj17-14-deps.txt")
DEP_PLUGIN = "org.apache.maven.plugins:maven-dependency-plugin:3.8.1:list"

REQUIRED = [
    ("org.apache.spark", "spark-core_2.12", "3.5.8"),
    ("org.scala-lang", "scala-library", "2.12.18"),
    ("org.apache.hadoop", "hadoop-client", "3.4.2"),
    ("org.apache.hbase", "hbase-client", "2.6.4"),
    ("org.apache.zookeeper", "zookeeper", "3.9.3"),
]
GROUP_VERSION = {
    "org.apache.spark": "3.5.8",
    "org.scala-lang": "2.12.18",
    "org.apache.hadoop": "3.4.2",
    "org.apache.hbase": "2.6.4",
    "org.apache.zookeeper": "3.9.3",
}
SCOPES = "compile|provided|runtime|test|system"
LINE = re.compile(r"^\s*([^:\s]+):([^:\s]+):([^:\s]+):(?:([^:\s]+):)?([^:\s]+):(%s)\b" % SCOPES)


def run_maven():
    mvn = "mvn.cmd" if os.name == "nt" else "mvn"
    cmd = [mvn, "-B", "-q", "-DskipTests", "compile", DEP_PLUGIN,
           "-DoutputFile=" + LIST_FILE, "-DappendOutput=false"]
    print("+ " + " ".join(cmd))
    if subprocess.call(cmd, cwd=ROOT) != 0:
        print("FAIL AC1: the build did not compile on this JDK (%s)" % java_version())
        sys.exit(1)


def java_version():
    try:
        out = subprocess.run(["java", "-version"], capture_output=True, text=True).stderr
        return out.splitlines()[0] if out else "unknown"
    except OSError:
        return "unknown"


def read_list(module):
    path = os.path.join(ROOT, module, LIST_FILE)
    if not os.path.isfile(path):
        return None
    deps = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            match = LINE.match(line)
            if match:
                group, artifact, _type, _classifier, version, scope = match.groups()
                deps.append((group, artifact, version, scope))
    return deps


def root_java_version():
    ns = {"m": "http://maven.apache.org/POM/4.0.0"}
    props = ET.parse(os.path.join(ROOT, "pom.xml")).getroot().find("m:properties", ns)
    node = props.find("m:java.version", ns) if props is not None else None
    return node.text.strip() if node is not None and node.text else None


def main():
    if "--no-build" not in sys.argv:
        run_maven()
    problems = []
    seen = set()
    for module in MODULES:
        deps = read_list(module)
        if deps is None:
            problems.append("%s: no dependency list at %s" % (module, os.path.join(module, LIST_FILE)))
            continue
        for group, artifact, version, scope in deps:
            seen.add((group, artifact, version))
            wanted = GROUP_VERSION.get(group)
            if wanted and version != wanted:
                problems.append("%s: %s:%s is %s (%s), expected %s" % (module, group, artifact, version, scope, wanted))
            if artifact.endswith("_2.11"):
                problems.append("%s: %s:%s:%s is built for Scala 2.11" % (module, group, artifact, version))
    for group, artifact, version in REQUIRED:
        if (group, artifact, version) not in seen:
            problems.append("%s:%s:%s is not resolved by any module" % (group, artifact, version))
    java = root_java_version()
    if java != "1.8":
        problems.append("root pom java.version is %s, expected 1.8 (this slice stays on Java 8)" % java)
    if problems:
        for problem in sorted(set(problems)):
            print("FAIL AC1: " + problem)
        print("FAIL AC1: %d problem(s)" % len(set(problems)))
        sys.exit(1)
    print("PASS AC1: all modules compile on %s against Spark 3.5.8, Scala 2.12.18, Hadoop 3.4.2, "
          "HBase 2.6.4, ZooKeeper 3.9.3, with no other version of those artifacts" % java_version())


if __name__ == "__main__":
    main()
