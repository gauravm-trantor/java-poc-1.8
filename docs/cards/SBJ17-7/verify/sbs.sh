#!/bin/sh
# Side-by-side for SBJ17-7: build the real artifacts from main and from the PR head, compare every class and resource.
V="$(cd "$(dirname -- "$0")" && pwd)"
S="$V/sbs"
rm -rf "$S"; mkdir -p "$S"
git clone -q "C:/Gaurav/Genpact RiskCanvas/POC/java-poc-1.8" "$S/main"
git -C "$S/main" checkout -q 1d0b183788a311f51cb4a210185f733d0ba3bf93
git clone -q --branch card/SBJ17-7-tests-any-order "C:/Gaurav/Genpact RiskCanvas/POC/java-poc-1.8" "$S/head"
for side in main head; do
  mvn -B -f "$S/$side/pom.xml" clean package -DskipTests > "$S/$side-build.log" 2>&1
  echo "$side build exit=$? sha=$(git -C "$S/$side" rev-parse --short HEAD)"
  (cd "$S/$side" && find . -path '*/target/classes/*' -type f ! -name '*.lst' | sort | xargs sha256sum) > "$S/$side-classes.sha"
  (cd "$S/$side" && find . -path '*/target/*.jar' -type f | sort) > "$S/$side-jars.txt"
done
echo "class/resource files: main $(wc -l < "$S/main-classes.sha"), head $(wc -l < "$S/head-classes.sha")"
if diff "$S/main-classes.sha" "$S/head-classes.sha" > "$S/classes.diff"; then echo "classes and resources: identical"; else echo "classes and resources: DIFFER"; cat "$S/classes.diff"; fi
diff "$S/main-jars.txt" "$S/head-jars.txt" && echo "jar list: identical: $(tr '\n' ' ' < "$S/head-jars.txt")"
for j in $(cat "$S/head-jars.txt"); do
  a=$(unzip -l "$S/main/$j" | awk 'NR>3{print $4}' | sort | grep -v '^$' | sha256sum); b=$(unzip -l "$S/head/$j" | awk 'NR>3{print $4}' | sort | grep -v '^$' | sha256sum)
  [ "$a" = "$b" ] && echo "entries same: $j" || echo "entries DIFFER: $j"
done
