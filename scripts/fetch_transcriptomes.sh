#!/usr/bin/env bash
#
# Fetch the AplysiaTools transcriptomes.
#
# P01-03.1. The pre-registration names the CNS transcriptome assembly as
# GenBank TSA GJYY00000000 (Orvis et al. 2022), "also via AplysiaTools".
# This is the AplysiaTools side of that pair.
#
#   scripts/fetch_transcriptomes.sh
#
# AplysiaTools publishes its files as plain files over HTTP, under
# http://aplysiatools.org/data/. The BLAST interface on port 4567 is a
# SequenceServer instance, and SequenceServer serves hits, not databases:
# there is no route that returns a whole database file. The files are on
# the web server, not behind the BLAST form.
#
# The publisher publishes NO checksum for any of these files. So there is
# nothing to verify against at the source. What there is instead is this
# repository's own committed record: data/manifest.tsv. A re-run of this
# script recomputes the SHA-256 and compares it with the manifest, so a
# file that has changed under us is detected rather than silently
# accepted. The manifest is the claim; this script checks it.
#
# The script is idempotent: it downloads what is absent and verifies what
# is present. It does not re-download.

set -euo pipefail

BASE="http://aplysiatools.org/data"
USER_AGENT="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$HERE")"
RAW="${ROOT}/data/raw"
MANIFEST="${ROOT}/data/manifest.tsv"

FILES=(
  "new_unigenes.fasta"
  "annotation_1A-2C.fasta"
  "current.annotation.fasta"
  "merged.unigenes.trinotate.longest_orf.json"
)

WHAT=(
  "the merged-unigene nucleotide FASTA"
  "the predicted protein set for the CNS transcriptome"
  "the live current annotation: every tissue's proteins in one file"
  "the Trinotate functional annotation of the merged unigenes"
)

mkdir -p "$RAW"

# The SHA-256 the manifest records for a file, if it records one.
manifest_sha256() {
  [ -f "$MANIFEST" ] || return 0
  awk -F'\t' -v file="$1" 'NR>1 && $1==file {print $8}' "$MANIFEST"
}

for INDEX in "${!FILES[@]}"; do
  FILE="${FILES[$INDEX]}"
  TARGET="${RAW}/${FILE}"
  echo "==> ${FILE}  (${WHAT[$INDEX]})"

  if [ ! -f "$TARGET" ]; then
    echo "    downloading"
    curl -fsSL --retry 5 --retry-delay 5 --max-time 1800 -A "$USER_AGENT" \
      "${BASE}/${FILE}" -o "${TARGET}.part"
    # The mount sometimes serves a stale directory listing. Confirm the
    # bytes landed before believing them.
    if [ ! -s "${TARGET}.part" ]; then
      echo "    the download produced nothing" >&2
      rm -f "${TARGET}.part"
      exit 1
    fi
    mv "${TARGET}.part" "$TARGET"
  else
    echo "    already here"
  fi

  BYTES="$(stat -c%s "$TARGET")"
  SHA256="$(sha256sum "$TARGET" | awk '{print $1}')"
  RECORDED="$(manifest_sha256 "$FILE")"

  if [ -n "$RECORDED" ]; then
    if [ "$RECORDED" = "$SHA256" ]; then
      echo "    ${BYTES} bytes, sha256 ${SHA256}"
      echo "    matches the checksum in data/manifest.tsv"
    else
      echo "    ${BYTES} bytes, sha256 ${SHA256}"
      echo "    DOES NOT MATCH the checksum in data/manifest.tsv (${RECORDED})" >&2
      echo "    the publisher serves no checksum, so the manifest is the only record" >&2
      exit 1
    fi
  else
    echo "    ${BYTES} bytes, sha256 ${SHA256}"
    echo "    not in data/manifest.tsv yet; run scripts/make_manifest.sh to record it"
  fi
done

echo
echo "no published checksum exists for any of these files; the record is data/manifest.tsv"
