#!/usr/bin/env bash
# Print the pinned tool manifest for all three environments, then run whatever
# was passed in.
#
# Usage:
#   ./scripts/environment.sh                       print the manifest
#   ./scripts/environment.sh micromamba run -n bio liftoff --help
set -uo pipefail
cat /opt/aplysia/ENVIRONMENT.txt 2>/dev/null \
  || echo "no manifest: the image was not built with the manifest stage"
if [ "$#" -gt 0 ]; then exec "$@"; fi
