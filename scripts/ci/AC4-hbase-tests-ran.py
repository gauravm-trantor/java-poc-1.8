"""AC4 the 2 HBase tests run, not skip.

Reads the Surefire report of SalesAggregatorHBaseTest after mvn -B clean test and passes only when both tests
ran and passed: tests=2, skipped=0, failures=0, errors=0. The test skips itself when no HBase answers on
localhost, and a skip is not a failure, so without this check a missing HBase would go unseen.

Usage: python scripts/ci/AC4-hbase-tests-ran.py [report.xml]
"""
import os
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
REPORT = os.path.join(ROOT, "spark-job", "target", "surefire-reports",
                      "TEST-com.example.salesbatch.spark.SalesAggregatorHBaseTest.xml")


def fail(message):
    print("FAIL: " + message)
    sys.exit(1)


def main():
    report = sys.argv[1] if len(sys.argv) > 1 else REPORT
    if not os.path.isfile(report):
        fail("no Surefire report for SalesAggregatorHBaseTest at %s (did mvn -B clean test run?)" % report)
    suite = ET.parse(report).getroot()
    counts = {key: int(suite.get(key, "0")) for key in ("tests", "skipped", "failures", "errors")}
    if counts["tests"] != 2:
        fail("expected 2 HBase tests, the report has %d" % counts["tests"])
    if counts["skipped"]:
        fail("%d of the 2 HBase tests were skipped: no HBase answered" % counts["skipped"])
    if counts["failures"] or counts["errors"]:
        fail("the HBase tests ran but %d failed and %d errored" % (counts["failures"], counts["errors"]))
    print("PASS AC4: the 2 HBase tests ran against HBase and passed, none skipped")


if __name__ == "__main__":
    main()
