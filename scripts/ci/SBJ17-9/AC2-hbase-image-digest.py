"""AC2 The HBase image in docker/local/docker-compose.yml is named by its sha256 digest, with the tag 1.4 kept
beside it for readers.

Passes only when the hbase service's image reads harisekhon/hbase:1.4@sha256:<64 hex>.

Usage: python scripts/ci/SBJ17-9/AC2-hbase-image-digest.py [compose file]
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pins  # noqa: E402

EXPECTED = re.compile(r"^harisekhon/hbase:1\.4@sha256:[0-9a-f]{64}$")


def main():
    image = pins.hbase_image(sys.argv[1] if len(sys.argv) > 1 else None)
    if image is None:
        print("AC2 FAIL: no image line in the hbase service")
        return 1
    if not EXPECTED.match(image):
        print("AC2 FAIL: hbase image is %s, expected harisekhon/hbase:1.4@sha256:<64 hex>" % image)
        return 1
    print("AC2 PASS: hbase image is %s" % image)
    return 0


if __name__ == "__main__":
    sys.exit(main())
