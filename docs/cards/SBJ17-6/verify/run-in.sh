#!/usr/bin/env bash
# Run the PR head's acceptance script (unchanged copy) with the working folder set to $1.
cd "$1" || exit 2
echo "Folder: $1 at $(git rev-parse --short HEAD)"
bash "$(dirname "$0")/head/docs/cards/SBJ17-6/acceptance.sh"
echo "exit=$?"
