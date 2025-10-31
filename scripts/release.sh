#!/bin/bash

set -euo pipefail

echo "This will release both backend and frontend packages with the same version."
echo "What type of version bump?"
select BUMP in "patch" "minor" "major"; do
  if [[ -n $BUMP ]]; then
    break
  fi
done

gh workflow run version-bump.yml -f bump_type=$BUMP
echo "Release workflow triggered for backend and frontend ($BUMP bump)"
