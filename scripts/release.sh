#!/bin/bash

set -euo pipefail

PACKAGES=("backend" "frontend")

echo "Which package do you want to release?"
select PACKAGE in "${PACKAGES[@]}"; do
  if [[ -n $PACKAGE ]]; then
    break
  fi
done

echo "What type of version bump?"
select BUMP in "patch" "minor" "major"; do
  if [[ -n $BUMP ]]; then
    break
  fi
done

gh workflow run version-bump.yml -f package=$PACKAGE -f bump_type=$BUMP
echo "Release workflow triggered for $PACKAGE ($BUMP bump)"


