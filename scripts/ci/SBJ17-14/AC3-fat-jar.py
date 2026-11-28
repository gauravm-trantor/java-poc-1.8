"""AC3 The Spark job's fat jar builds against those versions and bundles HBase 2.6.4's client, not Spark,
Hadoop or Scala.

Builds `mvn -B -DskipTests package` and lists the resolved artifacts of spark-job with their files, then reads
spark-job/target/spark-job-1.0.0-SNAPSHOT.jar. Passes only when:
- the jar holds org/apache/hadoop/hbase/client/ classes and
  META-INF/maven/org.apache.hbase/hbase-client/pom.properties says version=2.6.4;
- it holds no META-INF/maven/ folder of the groups org.apache.spark, org.scala-lang or org.apache.hadoop,
  and no entry under org/apache/spark/ or scala/;
- it holds no class that is also in a resolved jar of the groups org.apache.spark, org.scala-lang or
  org.apache.hadoop. Hadoop is checked by those jars' class lists, not by the org/apache/hadoop/ prefix,
  because HBase's own compat jars rightly put classes under org.apache.hadoop.metrics2. Third-party jars that
  Spark also depends on (ZooKeeper, commons, protobuf) are not Spark and may be bundled.

Usage: python3 scripts/ci/SBJ17-14/AC3-fat-jar.py [--no-build]
"""
import os
import re
import subprocess
import sys
import zipfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
JAR = os.path.join(ROOT, "spark-job", "target", "spark-job-1.0.0-SNAPSHOT.jar")
LIST_FILE = os.path.join("target", "sbj17-14-deps-files.txt")
DEP_PLUGIN = "org.apache.maven.plugins:maven-dependency-plugin:3.8.1:list"
EXCLUDED_GROUPS = ("org.apache.spark", "org.scala-lang", "org.apache.hadoop")
SCOPES = "compile|provided|runtime|test|system"
LINE = re.compile(r"^\s*([^:\s]+):([^:\s]+):([^:\s]+):(?:([^:\s]+):)?([^:\s]+):(%s):(.+?)(?:\s+--\s.*)?\s*$" % SCOPES)


def fail_all(problems):
    for problem in problems:
        print("FAIL AC3: " + problem)
    sys.exit(1)


def build():
    mvn = "mvn.cmd" if os.name == "nt" else "mvn"
    cmd = [mvn, "-B", "-q", "-DskipTests", "package", DEP_PLUGIN, "-DoutputAbsoluteArtifactFilename=true",
           "-DoutputFile=" + LIST_FILE, "-DappendOutput=false"]
    print("+ " + " ".join(cmd))
    if subprocess.call(cmd, cwd=ROOT) != 0:
        fail_all(["the fat jar did not build"])


def excluded_jars():
    path = os.path.join(ROOT, "spark-job", LIST_FILE)
    if not os.path.isfile(path):
        fail_all(["no dependency list at spark-job/%s" % LIST_FILE])
    jars = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            match = LINE.match(line)
            if match and match.group(1) in EXCLUDED_GROUPS:
                jars.append(("%s:%s:%s" % (match.group(1), match.group(2), match.group(5)), match.group(7).strip()))
    if not jars:
        fail_all(["no Spark, Scala or Hadoop jar in spark-job's resolved list; cannot check for overlap"])
    return jars


def classes(path):
    with zipfile.ZipFile(path) as archive:
        return {name for name in archive.namelist() if name.endswith(".class")}


def main():
    if "--no-build" not in sys.argv:
        build()
    if not os.path.isfile(JAR):
        fail_all(["no fat jar at %s" % os.path.relpath(JAR, ROOT)])
    problems = []
    with zipfile.ZipFile(JAR) as archive:
        names = archive.namelist()
        props_name = "META-INF/maven/org.apache.hbase/hbase-client/pom.properties"
        if not any(name.startswith("org/apache/hadoop/hbase/client/") and name.endswith(".class") for name in names):
            problems.append("no HBase client classes (org/apache/hadoop/hbase/client/)")
        if props_name in names:
            props = archive.read(props_name).decode("utf-8", "replace")
            version = re.search(r"^version=(.*)$", props, re.M)
            version = version.group(1).strip() if version else "none"
            if version != "2.6.4":
                problems.append("bundled hbase-client is %s, expected 2.6.4" % version)
        else:
            problems.append("no %s in the jar" % props_name)
    for group in EXCLUDED_GROUPS:
        found = sorted({n.split("/")[3] for n in names if n.startswith("META-INF/maven/%s/" % group) and n.count("/") > 3})
        if found:
            problems.append("bundles %s artifacts: %s" % (group, ", ".join(found)))
    for prefix in ("org/apache/spark/", "scala/"):
        count = sum(1 for n in names if n.startswith(prefix))
        if count:
            problems.append("%d entries under %s" % (count, prefix))
    bundled = {n for n in names if n.endswith(".class")}
    for coordinates, path in excluded_jars():
        if not os.path.isfile(path):
            problems.append("resolved jar missing on disk: %s (%s)" % (coordinates, path))
            continue
        overlap = bundled & classes(path)
        if overlap:
            problems.append("%d classes also in %s, e.g. %s" % (len(overlap), coordinates, sorted(overlap)[0]))
    if problems:
        fail_all(problems)
    print("PASS AC3: the fat jar bundles hbase-client 2.6.4 and no class of Spark, Scala or Hadoop")


if __name__ == "__main__":
    main()
