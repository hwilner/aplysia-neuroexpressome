#!/usr/bin/env bash
# Print the pinned tool manifest, then run whatever was passed in.
# Usage:  ./scripts/environment.sh python scripts/parse_gff.py
set -euo pipefail
cat /opt/aplysia/ENVIRONMENT.txt 2>/dev/null || echo "no manifest: image was not built with the manifest stage"
if [ "$#" -gt 0 ]; then exec "$@"; fi
