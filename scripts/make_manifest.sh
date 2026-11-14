#!/usr/bin/env bash
#
# Write data/manifest.tsv: the checksum record for every downloaded input.
#
# P01-02.4. The inputs are not committed, so this file is what says which
# bytes were used. It is committed, and it is the canonical record: a
# download can be verified against it without going to NCBI at all.
#
#   scripts/make_manifest.sh
#
# The manifest is regenerated, never hand-edited. If a file is missing the
# script fails rather than writing a manifest that is quietly short of a
# file, because a partial manifest reads like a complete one and the file
# it omits is exactly the one nobody checks.
#
# Columns:
#
#   file               the name of the file, as it sits in data/raw/
#   assembly           the RefSeq accession the file belongs to
#   annotation_release the NCBI annotation release the file belongs to
#   url                where it was fetched from
#   bytes              its size
#   md5                the MD5 NCBI publishes, where it publishes one
#   md5_source         whether that MD5 is published or was not available
#   sha256             the SHA-256, computed here
#   purpose            what the pre-registration uses it for
#
# The release strings themselves are captured verbatim in P01-02.5. The two
# release columns here say which release a file belongs to, which is what
# an anchor for a checksum is; they are not the verbatim capture.

set -euo pipefail

ASSEMBLY="GCF_000002075.1"
ASSEMBLY_NAME="AplCal3.0"
RELEASE="NCBI Aplysia californica Annotation Release 102"
BASE="https://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/000/002/075/${ASSEMBLY}_${ASSEMBLY_NAME}"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$HERE")"
RAW="${ROOT}/data/raw"
OUT="${ROOT}/data/manifest.tsv"

# The files, and what the pre-registration uses each for.
FILES=(
  "md5checksums.txt"
  "${ASSEMBLY}_${ASSEMBLY_NAME}_genomic.fna.gz"
  "${ASSEMBLY}_${ASSEMBLY_NAME}_genomic.gff.gz"
  "${ASSEMBLY}_${ASSEMBLY_NAME}_protein.faa.gz"
  "${ASSEMBLY}_${ASSEMBLY_NAME}_cds_from_genomic.fna.gz"
  "${ASSEMBLY}_${ASSEMBLY_NAME}_feature_table.txt.gz"
  "${ASSEMBLY}_${ASSEMBLY_NAME}_genomic_gaps.txt.gz"
  "${ASSEMBLY}_${ASSEMBLY_NAME}_gene_ontology.gaf.gz"
  "${ASSEMBLY}_${ASSEMBLY_NAME}_assembly_report.txt"
  "${ASSEMBLY}_${ASSEMBLY_NAME}_feature_count.txt.gz"
  "Aplysia_californica_AR102_annotation_report.xml"
  "README_Aplysia_californica_annotation_release_102"
)

PURPOSES=(
  "the publisher's checksum list for the assembly directory, from which the md5 column is taken"
  "the assembly: the lift-over target and the coordinate frame"
  "the gene models: parsed by step 3, and the --gff guide for Liftoff"
  "the protein set: BUSCO --proteins, InterProScan, eggNOG-mapper"
  "the CDS sequences: the start/stop-codon and coding-length diagnostics"
  "the flat attribute table: the gene and transcript names"
  "the gap positions: whether a model overlaps a gap in the assembly"
  "the GO annotations: the GO half of the gene-to-term map for test T6"
  "the sequence-to-assembly mapping, and the file stating both accessions"
  "NCBI's own counts of the annotation"
  "the Release 102 annotation report"
  "the release readme, which states the release strings"
)

# The assembly FASTA is the assembly; the rest are the Release 102
# distribution, which carries that assembly.
ANNOTATION_RELEASE=(
  "AplCal3.0 assembly directory"
  "${ASSEMBLY_NAME} assembly"
  "${RELEASE}" "${RELEASE}" "${RELEASE}" "${RELEASE}" "${RELEASE}"
  "${RELEASE}" "${RELEASE}" "${RELEASE}" "${RELEASE}" "${RELEASE}"
)

if [ ! -f "${RAW}/md5checksums.txt" ]; then
  echo "==> fetching the published checksum list"
  curl -fsSL --retry 5 --retry-delay 5 --max-time 120 \
    "${BASE}/md5checksums.txt" -o "${RAW}/md5checksums.txt"
fi

echo "==> checking that every file is present"
MISSING=0
for FILE in "${FILES[@]}"; do
  if [ ! -f "${RAW}/${FILE}" ]; then
    echo "    MISSING ${FILE}" >&2
    MISSING=1
  fi
done
if [ "$MISSING" -ne 0 ]; then
  echo "the manifest is not written: run scripts/fetch_assembly.sh and scripts/fetch_annotation.sh first" >&2
  exit 1
fi

echo "==> computing the checksums"
{
  printf 'file\tassembly\tannotation_release\turl\tbytes\tmd5\tmd5_source\tsha256\tpurpose\n'
  INDEX=0
  for FILE in "${FILES[@]}"; do
    TARGET="${RAW}/${FILE}"
    BYTES="$(stat -c%s "$TARGET")"
    SHA256="$(sha256sum "$TARGET" | awk '{print $1}')"
    PUBLISHED="$(awk -v file="$FILE" '$2 ~ file"$" {print $1}' "${RAW}/md5checksums.txt")"
    if [ -n "$PUBLISHED" ]; then
      ACTUAL_MD5="$(md5sum "$TARGET" | awk '{print $1}')"
      if [ "$ACTUAL_MD5" != "$PUBLISHED" ]; then
        echo "md5 mismatch for ${FILE}" >&2
        echo "  expected ${PUBLISHED}" >&2
        echo "  got      ${ACTUAL_MD5}" >&2
        exit 1
      fi
      MD5="${PUBLISHED}"
      SOURCE="published by NCBI"
    else
      MD5="-"
      SOURCE="none published"
    fi
    printf '%s\t%s\t%s\t%s/%s\t%s\t%s\t%s\t%s\t%s\n' \
      "$FILE" "$ASSEMBLY" "${ANNOTATION_RELEASE[$INDEX]}" "$BASE" "$FILE" \
      "$BYTES" "$MD5" "$SOURCE" "$SHA256" "${PURPOSES[$INDEX]}"
    INDEX=$((INDEX + 1))
  done
} > "${OUT}.new"

mv "${OUT}.new" "${OUT}"
echo "==> wrote ${OUT} with $((${#FILES[@]})) files"
