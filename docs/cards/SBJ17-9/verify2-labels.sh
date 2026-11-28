#!/bin/sh
# Resolve main's moving labels today, and the HBase tag's digest; compare compose files.
V="$1"
for pair in "actions/checkout v7" "actions/setup-python v7" "actions/setup-java v6" "actions/upload-artifact v7" "actions/setup-node v7"; do
  set -- $pair
  o=$(gh api "repos/$1/git/ref/tags/$2" --jq '.object.type+" "+.object.sha')
  t=$(echo "$o" | cut -d' ' -f1); s=$(echo "$o" | cut -d' ' -f2)
  if [ "$t" = tag ]; then s=$(gh api "repos/$1/git/tags/$s" --jq .object.sha); fi
  echo "$1@$2 today -> $s"
done
echo "--- compose image lines, main then head"
grep -n "image:" "$V/main/docker/local/docker-compose.yml"
grep -n "image:" "$V/head/docker/local/docker-compose.yml"
echo "--- registry"
docker buildx imagetools inspect harisekhon/hbase:1.4 2>&1 | head -4
