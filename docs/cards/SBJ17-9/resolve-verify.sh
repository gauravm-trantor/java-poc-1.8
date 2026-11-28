#!/bin/sh
# Verify, SBJ17-9: resolve each moving label on main and each release named in a pin comment to its commit today.
for p in "checkout v7 v7.0.1" "setup-python v7 v7.1.0" "setup-java v6 v6.3.0" "setup-node v7 v7.1.0" "upload-artifact v7 v7.0.2"; do
  set -- $p
  a=$(gh api "repos/actions/$1/commits/$2" --jq .sha)
  b=$(gh api "repos/actions/$1/commits/$3" --jq .sha)
  echo "$1 $2=$a $3=$b"
done
