#!/bin/bash
# AC4 Sample-data run through the whole flow (upload, Spark job, approval, publish) gives a byte-identical
# report-<date>.csv from main's build and this build, both on Java 8 in Linux containers.
#
# Two sides, one after the other: "old" (OLD_REF, default origin/main) and "new" (NEW_REF, default HEAD).
# Each side, from a fresh clone (line ends as committed):
#   1. builds with `mvn -B -DskipTests package` in a Corretto 8 Maven container;
#   2. builds its own runtime image from its docker/Dockerfile (Java 8 + its Spark);
#   3. starts its own HBase from its docker/local/docker-compose.yml (project sbj1714-<side>, no published
#      ports, so it never meets a developer's own sales-hbase);
#   4. runs workflow-app's WorkflowServer inside its runtime image with spark.master=local[*], so the side's
#      own spark-submit runs the side's own fat jar against the side's own HBase;
#   5. uploads each input as the UI does (POST /batches/upload), waits for WAITING_APPROVAL, approves, waits
#      for COMPLETED and keeps report-<date>.csv;
#   6. records its HBase and Spark versions and its table layout (AC5-layout.rb) for AC5.
# Pass: for every input both reports exist, are not empty and `cmp` finds them identical, AND the new side
# really ran the new stack: HBase 2.6.4 and Spark 3.5.8. Without that check the two sides would be the same
# stack before the build, and the test would pass.
#
# Inputs: sample-data/sales-20261113.csv and sales-20261115.csv (the 2 good sample files).
# Output: $SBS_OUT (default target/sbj17-14-sbs): <side>/reports/, <side>/versions.txt, <side>/layout.txt,
# <side>/*.log, summary.txt. AC5-table-layout.sh reads the same folder.
# Usage: bash scripts/ci/SBJ17-14/AC4-report-side-by-side.sh
set -u
export MSYS_NO_PATHCONV=1

REPO=$(cd "$(dirname "$0")/../../.." && pwd)
OUT="${SBS_OUT:-$REPO/target/sbj17-14-sbs}"
OLD_REF="${OLD_REF:-origin/main}"
NEW_REF="${NEW_REF:-HEAD}"
MAVEN_IMAGE="maven:3.9.9-amazoncorretto-8@sha256:1f67afafc8ff766a0ba4b0fa389054cf57083ed4a067a3c6a2126e9ddeb927f8"
M2_VOLUME="sbj1714-m2"
INPUTS="20261113 20261115"
LAYOUT_RB="$REPO/scripts/ci/SBJ17-14/AC5-layout.rb"

hostpath() { if command -v cygpath >/dev/null 2>&1; then cygpath -m "$1"; else printf '%s' "$1"; fi; }
log() { echo "[sbs $(date -u +%H:%M:%S)] $*"; }

cleanup_side() {
  side=$1
  docker rm -f "sbj1714-app-$side" >/dev/null 2>&1
  if [ -f "$OUT/$side/src/docker/local/docker-compose.yml" ]; then
    docker compose -p "sbj1714-$side" -f "$(hostpath "$OUT/$side/src/docker/local/docker-compose.yml")" \
      -f "$(hostpath "$OUT/$side/override.yml")" down -v >/dev/null 2>&1
  fi
}
trap 'cleanup_side old; cleanup_side new' EXIT

run_side() {
  side=$1 ref=$2
  dir="$OUT/$side" src="$OUT/$side/src"
  rm -rf "$dir" && mkdir -p "$dir/reports"
  sha=$(git -C "$REPO" rev-parse "$ref") || { echo "side $side: unknown ref $ref" > "$dir/error.txt"; return 1; }
  log "$side: $ref = $sha"
  echo "ref=$ref sha=$sha" > "$dir/versions.txt"
  git clone -q -c core.autocrlf=false "$REPO" "$src" && git -C "$src" -c advice.detachedHead=false checkout -q "$sha" \
    || { echo "clone failed" > "$dir/error.txt"; return 1; }

  log "$side: build (Corretto 8, Maven)"
  docker run --rm -v "$(hostpath "$src"):/src" -v "$M2_VOLUME:/root/.m2" -w /src "$MAVEN_IMAGE" \
    mvn -B -q -DskipTests package > "$dir/build.log" 2>&1 \
    || { echo "build failed, see build.log" > "$dir/error.txt"; tail -40 "$dir/build.log"; return 1; }

  log "$side: runtime image"
  docker build -q -t "sbj1714-runtime-$side" "$(hostpath "$src/docker")" > "$dir/image.log" 2>&1 \
    || { echo "runtime image failed, see image.log" > "$dir/error.txt"; tail -40 "$dir/image.log"; return 1; }

  log "$side: HBase"
  hbase="sbj1714-hbase-$side"
  printf 'services:\n  hbase:\n    container_name: %s\n    ports: !reset []\n' "$hbase" > "$dir/override.yml"
  docker compose -p "sbj1714-$side" -f "$(hostpath "$src/docker/local/docker-compose.yml")" \
    -f "$(hostpath "$dir/override.yml")" up -d --build hbase > "$dir/hbase-up.log" 2>&1 \
    || { echo "HBase did not start, see hbase-up.log" > "$dir/error.txt"; tail -40 "$dir/hbase-up.log"; return 1; }
  ready=""
  for i in $(seq 1 60); do
    if echo "list" | docker exec -i "$hbase" hbase shell -n > /dev/null 2>&1; then ready=1; break; fi
    sleep 5
  done
  [ -n "$ready" ] || { docker logs "$hbase" > "$dir/hbase.log" 2>&1; echo "HBase not ready in 5 min" > "$dir/error.txt"; return 1; }
  hbase_ip=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$hbase")
  network=$(docker inspect -f '{{range $k, $v := .NetworkSettings.Networks}}{{$k}}{{end}}' "$hbase")
  echo "hbase=$(docker exec "$hbase" hbase version 2>/dev/null | sed -n 's/^HBase \([0-9][0-9.]*\).*/\1/p' | head -1)" >> "$dir/versions.txt"

  log "$side: workflow-app"
  app="sbj1714-app-$side"
  docker run -d --name "$app" --network "$network" --add-host "host.docker.internal:$hbase_ip" \
    -v "$(hostpath "$src"):/work" -v "$(hostpath "$dir/reports"):/reports" -w /work "sbj1714-runtime-$side" \
    java -Duser.timezone=UTC -Dserver.port=8080 -Dspark.master='local[*]' -Dspark.hbase.site= \
      -Dspark.job.jar=/work/spark-job/target/spark-job-1.0.0-SNAPSHOT.jar -Dreport.dir=/reports \
      -cp /conf:/work/workflow-app/target/workflow-app.jar com.example.salesbatch.workflow.WorkflowServer \
    > /dev/null || { echo "app did not start" > "$dir/error.txt"; return 1; }
  echo "spark=$(docker exec "$app" spark-submit --version 2>&1 | sed -n 's/.*version \([0-9][0-9.]*\).*/\1/p' | head -1)" >> "$dir/versions.txt"
  echo "java=$(docker exec "$app" java -version 2>&1 | head -1)" >> "$dir/versions.txt"
  up=""
  for i in $(seq 1 60); do
    if docker exec "$app" curl -s -o /dev/null http://localhost:8080/ ; then up=1; break; fi
    sleep 2
  done
  [ -n "$up" ] || { docker logs "$app" > "$dir/app.log" 2>&1; echo "app not up in 2 min" > "$dir/error.txt"; return 1; }

  for date in $INPUTS; do
    log "$side: $date upload"
    reply=$(docker exec "$app" curl -s -F "file=@/work/sample-data/sales-$date.csv" -F "businessDate=$date" \
      http://localhost:8080/batches/upload)
    id=$(printf '%s' "$reply" | sed -n 's/.*"processInstanceId" *: *"\([^"]*\)".*/\1/p')
    [ -n "$id" ] || { echo "$date: upload reply: $reply" >> "$dir/error.txt"; continue; }
    if ! wait_status "$app" "$id" WAITING_APPROVAL 120; then echo "$date: never WAITING_APPROVAL" >> "$dir/error.txt"; continue; fi
    docker exec "$app" curl -s -X POST "http://localhost:8080/batches/$id/approve?approved=true&approver=sbs" > /dev/null
    if ! wait_status "$app" "$id" COMPLETED 60; then echo "$date: never COMPLETED" >> "$dir/error.txt"; continue; fi
    log "$side: $date published"
  done

  docker exec -i "$hbase" hbase shell -n < "$LAYOUT_RB" 2>/dev/null | grep '^LAYOUT ' > "$dir/layout.txt"
  docker logs "$app" > "$dir/app.log" 2>&1
  cleanup_side "$side"
  return 0
}

# wait_status <app> <id> <status> <tries of 5 s>; stops early on FAILED or REJECTED
wait_status() {
  for i in $(seq 1 "$4"); do
    body=$(docker exec "$1" curl -s "http://localhost:8080/batches/$2")
    case "$body" in
      *"\"$3\""*) return 0 ;;
      *'"FAILED"'*|*'"REJECTED"'*) echo "$body" >> "$OUT/last-failure.txt"; return 1 ;;
    esac
    sleep 5
  done
  return 1
}

mkdir -p "$OUT"
docker volume create "$M2_VOLUME" > /dev/null
run_side old "$OLD_REF"
run_side new "$NEW_REF"

status=0
summary="$OUT/summary.txt"
: > "$summary"
for side in old new; do
  [ -f "$OUT/$side/error.txt" ] && { echo "FAIL AC4: $side side: $(tr '\n' ' ' < "$OUT/$side/error.txt")" | tee -a "$summary"; status=1; }
  echo "$side: $(tr '\n' ' ' < "$OUT/$side/versions.txt" 2>/dev/null)" | tee -a "$summary"
done
for date in $INPUTS; do
  a="$OUT/old/reports/report-$date.csv" b="$OUT/new/reports/report-$date.csv"
  if [ ! -s "$a" ] || [ ! -s "$b" ]; then
    echo "FAIL AC4: report-$date.csv missing or empty (old: $( [ -s "$a" ] && echo yes || echo no ), new: $( [ -s "$b" ] && echo yes || echo no ))" | tee -a "$summary"
    status=1
  elif cmp -s "$a" "$b"; then
    echo "same: report-$date.csv ($(wc -c < "$a") bytes)" | tee -a "$summary"
  else
    echo "FAIL AC4: report-$date.csv differs" | tee -a "$summary"
    diff "$a" "$b" | head -20 | tee -a "$summary"
    status=1
  fi
done
new_hbase=$(sed -n 's/^hbase=//p' "$OUT/new/versions.txt" 2>/dev/null)
new_spark=$(sed -n 's/^spark=//p' "$OUT/new/versions.txt" 2>/dev/null)
[ "$new_hbase" = "2.6.4" ] || { echo "FAIL AC4: new side ran HBase '${new_hbase:-none}', expected 2.6.4" | tee -a "$summary"; status=1; }
[ "$new_spark" = "3.5.8" ] || { echo "FAIL AC4: new side ran Spark '${new_spark:-none}', expected 3.5.8" | tee -a "$summary"; status=1; }
[ $status -eq 0 ] && echo "PASS AC4: both reports byte-identical between $OLD_REF and $NEW_REF; new side on HBase 2.6.4 and Spark 3.5.8" | tee -a "$summary"
exit $status
