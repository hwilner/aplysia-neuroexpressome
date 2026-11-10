#!/usr/bin/env bash
#
# Fetch the AplCal3.0 assembly FASTA and verify it.
#
# P01-02.2. The assembly is not committed: it is large, and it is
# re-fetchable from the accession recorded in the pre-registration. What is
# committed is this script and the record of what it fetched, so that the
# input can be verified rather than trusted.
#
#   scripts/fetch_assembly.sh [destination]
#
# The destination defaults to data/raw, relative to the repository root.
#
# The verification is threefold and each check catches something the others
# do not:
#
#   1. the MD5 against the checksum NCBI publishes beside the file, which
#      catches a truncated or corrupted transfer;
#   2. gzip -t, which catches a file that is complete by its length but
#      corrupt inside;
#   3. the SHA-256, printed for the record, because the programme's
#      canonical checksum list is data/manifest.tsv and that is written in
#      P01-02.4.
#
# The accession is GCF_000002075.1, and that is what NCBI's own annotation
# release readme states. See docs/P01-02-2-assembly-download.md.

set -euo pipefail

ASSEMBLY="GCF_000002075.1_AplCal3.0"
BASE="https://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/000/002/075/${ASSEMBLY}"
FILE="${ASSEMBLY}_genomic.fna.gz"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$HERE")"
DEST="${1:-${ROOT}/data/raw}"

mkdir -p "$DEST"
TARGET="${DEST}/${FILE}"

echo "==> fetching the published checksum list"
curl -fsSL --retry 5 --retry-delay 5 --max-time 120 \
  "${BASE}/md5checksums.txt" -o "${DEST}/md5checksums.txt"

EXPECTED="$(awk -v file="$FILE" '$2 ~ file"$" {print $1}' "${DEST}/md5checksums.txt")"
if [ -z "$EXPECTED" ]; then
  echo "no published checksum for ${FILE}" >&2
  exit 1
fi
echo "    published md5 ${EXPECTED}"

if [ -f "$TARGET" ]; then
  echo "==> ${TARGET} is already there; checking it rather than fetching it again"
else
  echo "==> downloading ${FILE} (about 229 MB)"
  curl -fL --retry 5 --retry-delay 5 --connect-timeout 30 \
    -o "${TARGET}" "${BASE}/${FILE}"
fi

echo "==> verifying the transfer against the published checksum"
ACTUAL_MD5="$(md5sum "$TARGET" | awk '{print $1}')"
if [ "$ACTUAL_MD5" != "$EXPECTED" ]; then
  echo "md5 mismatch for ${TARGET}" >&2
  echo "  expected ${EXPECTED}" >&2
  echo "  got      ${ACTUAL_MD5}" >&2
  exit 1
fi
echo "    md5 ${ACTUAL_MD5} matches the published checksum"

echo "==> checking that the file is intact gzip"
gzip -t "$TARGET"
echo "    gzip integrity is good"

echo "==> recording the size and the sha256"
BYTES="$(stat -c%s "$TARGET")"
SHA256="$(sha256sum "$TARGET" | awk '{print $1}')"

cat <<RECORD
{
  "file": "${FILE}",
  "assembly": "GCF_000002075.1",
  "assembly_name": "AplCal3.0",
  "url": "${BASE}/${FILE}",
  "bytes": ${BYTES},
  "md5": "${ACTUAL_MD5}",
  "sha256": "${SHA256}"
}
RECORD
