#!/usr/bin/env bash
#
# Fetch the RefSeq Release 102 annotation for AplCal3.0 and its supporting files.
#
# P01-02.3. The annotation is not committed: it is re-fetchable from the
# accession, and what is committed is this script and the record of what it
# fetched, so that the input can be verified rather than trusted.
#
#   scripts/fetch_annotation.sh [destination]
#
# The destination defaults to data/raw, relative to the repository root.
#
# Which files, and why each one is here:
#
#   genomic.gff.gz           the gene models. Step 3 parses the GFF, and
#                            Liftoff takes it as the --gff guide.
#   protein.faa.gz           the annotation's protein set. BUSCO runs
#                            --proteins against it for the "before" arm, and
#                            InterProScan and eggNOG-mapper read it.
#   cds_from_genomic.fna.gz  the CDS sequences, for the start/stop codon and
#                            coding-length diagnostics of step 3.
#   feature_table.txt.gz     the flat attribute table, and the source of the
#                            gene and transcript names.
#   genomic_gaps.txt.gz      the gap positions. Step 3 asks whether a model
#                            overlaps a gap in the assembly.
#   gene_ontology.gaf.gz     the GO annotations, the GO half of the
#                            gene-to-term map that test T6 is run against.
#   assembly_report.txt      the sequence-to-assembly mapping, and the file
#                            that states both accessions.
#   feature_count.txt.gz     the counts, for the record.
#
# Two more files carry the release documentation rather than data: the
# Release 102 annotation report, and the readme that states the release
# strings verbatim. NCBI publishes no checksum for either, so they are
# verified only for integrity and recorded by SHA-256 - the script says so
# rather than implying a check it did not do.
#
# Not fetched, deliberately: the GTF and the GenBank flat file are the same
# annotation in other formats, and the Gnomon models and the evidence
# alignments are NCBI's own predictions and alignments, not the curated
# annotation this project works from.

set -euo pipefail

ASSEMBLY="GCF_000002075.1_AplCal3.0"
BASE="https://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/000/002/075/${ASSEMBLY}"
PREFIX="${ASSEMBLY}_"

# The files, with a note of what each is for.
FILES=(
  "${PREFIX}genomic.gff.gz"
  "${PREFIX}protein.faa.gz"
  "${PREFIX}cds_from_genomic.fna.gz"
  "${PREFIX}feature_table.txt.gz"
  "${PREFIX}genomic_gaps.txt.gz"
  "${PREFIX}gene_ontology.gaf.gz"
  "${PREFIX}assembly_report.txt"
  "${PREFIX}feature_count.txt.gz"
  "Aplysia_californica_AR102_annotation_report.xml"
  "README_Aplysia_californica_annotation_release_102"
)

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$HERE")"
DEST="${1:-${ROOT}/data/raw}"

mkdir -p "$DEST"

echo "==> fetching the published checksum list"
curl -fsSL --retry 5 --retry-delay 5 --max-time 120 \
  "${BASE}/md5checksums.txt" -o "${DEST}/md5checksums.txt"

echo
echo "==> fetching the annotation"
FIRST=1
for FILE in "${FILES[@]}"; do
  TARGET="${DEST}/${FILE}"

  if [ -f "$TARGET" ]; then
    echo "    ${FILE} is already here; checking it rather than fetching it again"
  else
    if [ "$FIRST" -eq 1 ]; then
      echo "    downloading:"
      FIRST=0
    fi
    curl -fsSL --retry 5 --retry-delay 5 --connect-timeout 30 \
      -o "${TARGET}" "${BASE}/${FILE}"
    echo "      got ${FILE}"
  fi

  EXPECTED="$(awk -v file="$FILE" '$2 ~ file"$" {print $1}' "${DEST}/md5checksums.txt")"
  if [ -n "$EXPECTED" ]; then
    ACTUAL_MD5="$(md5sum "$TARGET" | awk '{print $1}')"
    if [ "$ACTUAL_MD5" != "$EXPECTED" ]; then
      echo "md5 mismatch for ${FILE}" >&2
      echo "  expected ${EXPECTED}" >&2
      echo "  got      ${ACTUAL_MD5}" >&2
      exit 1
    fi
    VERIFIED="md5 against the published checksum"
  else
    # No published checksum for this one. Saying so is the point: a file
    # that was only checked for integrity must not read as one that was
    # checked against the publisher.
    VERIFIED="no published checksum; integrity and sha256 only"
  fi

  case "$FILE" in
    *.gz) gzip -t "$TARGET" ;;
  esac

  BYTES="$(stat -c%s "$TARGET")"
  SHA256="$(sha256sum "$TARGET" | awk '{print $1}')"
  cat <<RECORD
{
  "file": "${FILE}",
  "assembly": "GCF_000002075.1",
  "assembly_name": "AplCal3.0",
  "annotation_release": "NCBI Aplysia californica Annotation Release 102",
  "url": "${BASE}/${FILE}",
  "bytes": ${BYTES},
  "sha256": "${SHA256}",
  "verified": "${VERIFIED}"
}
RECORD
done
