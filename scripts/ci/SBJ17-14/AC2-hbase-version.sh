#!/bin/sh
# AC2 The HBase the 2 HBase tests ran against is HBase 2.6.4, started from the repository's own image.
#
# Run after the maven job's tests. The existing scripts/ci/AC4-hbase-tests-ran.py proves the 2 tests ran,
# not skipped; this proves what they ran against: the container's `hbase version` reports 2.6.4 and the
# container runs the image docker/local/docker-compose.yml builds from docker/hbase/ (salesbatch-hbase:2.6.4).
#
# Usage: sh scripts/ci/SBJ17-14/AC2-hbase-version.sh [container, default sales-hbase]
container="${1:-sales-hbase}"
expected_image="salesbatch-hbase:2.6.4"

image=$(docker inspect --format '{{.Config.Image}}' "$container" 2>/dev/null)
if [ -z "$image" ]; then
  echo "FAIL AC2: no container named $container"
  exit 1
fi
version=$(docker exec "$container" hbase version 2>/dev/null | sed -n 's/^HBase \([0-9][0-9.]*\).*/\1/p' | head -1)

status=0
if [ "$version" != "2.6.4" ]; then
  echo "FAIL AC2: $container reports HBase '${version:-none}', expected 2.6.4"
  status=1
fi
if [ "$image" != "$expected_image" ]; then
  echo "FAIL AC2: $container runs image $image, expected $expected_image built from docker/hbase/"
  status=1
fi
[ $status -eq 0 ] && echo "PASS AC2: $container runs HBase 2.6.4 from $expected_image"
exit $status
