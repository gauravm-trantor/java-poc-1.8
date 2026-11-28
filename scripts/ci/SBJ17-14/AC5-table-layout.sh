#!/bin/sh
# AC5 The HBase table layout is unchanged (same tables, families, split points).
#
# Reads the layouts AC4-report-side-by-side.sh recorded on each side after the whole flow ran, so the tables
# are the ones the application itself created (HBaseTables, through workflow-app's initSchema). Each layout is
# the output of AC5-layout.rb: every user table, its column families with the attributes both HBase versions
# know, and its region start keys. Pass: both layouts hold the three tables, they are identical, and the new
# side ran HBase 2.6.4 (otherwise both sides are the same HBase and the check proves nothing).
#
# Usage: sh scripts/ci/SBJ17-14/AC5-table-layout.sh [side-by-side folder, default target/sbj17-14-sbs]
REPO=$(cd "$(dirname "$0")/../../.." && pwd)
OUT="${1:-${SBS_OUT:-$REPO/target/sbj17-14-sbs}}"
old="$OUT/old/layout.txt" new="$OUT/new/layout.txt"
status=0
for f in "$old" "$new"; do
  for table in sales_raw sales_agg batch_audit; do
    grep -q "^LAYOUT table $table\$" "$f" 2>/dev/null || { echo "FAIL AC5: no table $table in $f"; status=1; }
  done
done
if [ $status -eq 0 ] && ! cmp -s "$old" "$new"; then
  echo "FAIL AC5: the table layout differs (old < > new):"
  diff "$old" "$new"
  status=1
fi
new_hbase=$(sed -n 's/^hbase=//p' "$OUT/new/versions.txt" 2>/dev/null)
[ "$new_hbase" = "2.6.4" ] || { echo "FAIL AC5: new side ran HBase '${new_hbase:-none}', expected 2.6.4"; status=1; }
[ $status -eq 0 ] && echo "PASS AC5: $(grep -c '^LAYOUT table ' "$new") tables, their families and split points identical on HBase $(sed -n 's/^hbase=//p' "$OUT/old/versions.txt") and 2.6.4"
exit $status
