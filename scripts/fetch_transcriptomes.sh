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
TSA_BASE="https://ftp.ncbi.nlm.nih.gov/genbank/tsa/G"
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
  "tsa.GJYY.1.fsa_nt.gz"
  "tsa.GJYY.1.gbff.gz"
  "tsa.GJYY.mstr.gbff.gz"
  "stats.tsa.GJYY"
)

WHAT=(
  "the merged-unigene nucleotide FASTA"
  "the predicted protein set for the CNS transcriptome"
  "the live current annotation: every tissue's proteins in one file"
  "the Trinotate functional annotation of the merged unigenes"
  "the Orvis 2022 CNS transcriptome, from GenBank TSA GJYY00000000"
  "the same transcriptome in GenBank flatfile format: its DEFINITION lines carry the original names"
  "the TSA master record: the deposition's own metadata"
  "the publisher's own counts for the TSA project"
)

# Where each file comes from. The first four are AplysiaTools; the last
# three are the GenBank Transcriptome Shotgun Assembly.
URLS=(
  "${BASE}/new_unigenes.fasta"
  "${BASE}/annotation_1A-2C.fasta"
  "${BASE}/current.annotation.fasta"
  "${BASE}/merged.unigenes.trinotate.longest_orf.json"
  "${TSA_BASE}/tsa.GJYY.1.fsa_nt.gz"
  "${TSA_BASE}/tsa.GJYY.1.gbff.gz"
  "${TSA_BASE}/tsa.GJYY.mstr.gbff.gz"
  "${TSA_BASE}/stats.tsa.GJYY"
)

mkdir -p "$RAW"

# The SHA-256 the manifest records for a file, if it records one.
manifest_sha256() {
  [ -f "$MANIFEST" ] || return 0
  awk -F'\t' -v file="$1" 'NR>1 && $1==file {print $8}' "$MANIFEST"
}

# The publisher publishes no checksum for the TSA files either. But it does
# publish aggregates, in stats.tsa.GJYY: the number of sequences, the total
# base count, and the longest and shortest sequence. That is a real check,
# and a stronger one than a checksum of a file we already have.
verify_tsa_aggregates() {
  local FASTA="${RAW}/tsa.GJYY.1.fsa_nt.gz"
  local STATS="${RAW}/stats.tsa.GJYY"
  [ -f "$FASTA" ] && [ -f "$STATS" ] || {
    echo "    the TSA FASTA or its stats file is missing; skipping" >&2
    return 0
  }
  local EXPECTED
  # The stats file is pipe-separated key/value pairs:
  #   NCBI_TSA_master|GJYY|01|NT-Sequences|68308|Basepairs|...|NT-Smallest|303
  EXPECTED="$(awk -F'|' '
    $4=="NT-Sequences" {n=$5} $6=="Basepairs" {b=$7}
    $8=="NT-Largest" {l=$9} $10=="NT-Smallest" {s=$11}
    END {print n" "b" "l" "s}' "$STATS")"
  local ACTUAL
  ACTUAL="$(gzip -dc "$FASTA" | awk '
    BEGIN {mn = 1e18; mx = 0}
    /^>/ {if (n > 0) {tot += len; if (len < mn) mn = len; if (len > mx) mx = len}
          n++; len = 0; next}
    {len += length($0)}
    END {tot += len; if (n == 1 || len < mn) mn = len; if (len > mx) mx = len
         print n" "tot" "mx" "mn}')"
  if [ "$EXPECTED" = "$ACTUAL" ]; then
    echo "    ${ACTUAL} sequences, bases, longest, shortest"
    echo "    matches the publisher's published aggregates exactly"
  else
    echo "    the file does not match the publisher's published aggregates" >&2
    echo "      expected: ${EXPECTED}" >&2
    echo "      got:      ${ACTUAL}" >&2
    exit 1
  fi
}

for INDEX in "${!FILES[@]}"; do
  FILE="${FILES[$INDEX]}"
  TARGET="${RAW}/${FILE}"
  echo "==> ${FILE}  (${WHAT[$INDEX]})"

  if [ ! -f "$TARGET" ]; then
    echo "    downloading"
    curl -fsSL --retry 5 --retry-delay 5 --max-time 1800 -A "$USER_AGENT" \
      "${URLS[$INDEX]}" -o "${TARGET}.part"
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
echo "==> verifying the TSA FASTA against the publisher's published aggregates"
verify_tsa_aggregates
echo
echo "no published checksum exists for any of these files; the record is data/manifest.tsv"
