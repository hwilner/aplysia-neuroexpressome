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

# The transcriptome. The pre-registration names the GenBank TSA project
# the Orvis 2022 assembly was deposited under, and AplysiaTools as the
# other place to get the same build.
TSA="GJYY00000000"
TRANSCRIPTOME="Orvis et al. 2022 CNS transcriptome"
# The AplysiaTools files are from four different years, and three of them
# are not part of the GenBank TSA project at all. The accession column says
# which project a file belongs to; for those three it is "none".
TOOLS_2020="AplysiaTools merged unigenes, 2020 build"
TOOLS_CNS="AplysiaTools CNS set"
TOOLS_CURRENT="AplysiaTools current annotation"
TOOLS_BASE="http://aplysiatools.org/data"
TSA_BASE="https://ftp.ncbi.nlm.nih.gov/genbank/tsa/G"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$HERE")"
RAW="${ROOT}/data/raw"
OUT="${ROOT}/data/manifest.tsv"

# The files, and what the pre-registration uses each for.
#
# Each row is: file | accession | release | url | purpose
#
# The accession is what the file belongs to. For the genome and its
# annotation that is a RefSeq assembly accession; for the GenBank
# transcriptomes it is the TSA project the Orvis 2022 assembly was
# deposited under. For the AplysiaTools files it is "none" unless the file
# is part of that project: the 2020 merged unigenes are an earlier build,
# and the current annotation spans seven tissues, six of which are not in
# the project at all. P01-03.5 established which build the project runs
# on; the decision itself is recorded in data/authoritative-build.tsv.
ROWS=(
  "md5checksums.txt|${ASSEMBLY}|AplCal3.0 assembly directory|${BASE}/md5checksums.txt|the publisher's checksum list for the assembly directory, from which the md5 column is taken"
  "${ASSEMBLY}_${ASSEMBLY_NAME}_genomic.fna.gz|${ASSEMBLY}|${ASSEMBLY_NAME} assembly|${BASE}/${ASSEMBLY}_${ASSEMBLY_NAME}_genomic.fna.gz|the assembly: the lift-over target and the coordinate frame"
  "${ASSEMBLY}_${ASSEMBLY_NAME}_genomic.gff.gz|${ASSEMBLY}|${RELEASE}|${BASE}/${ASSEMBLY}_${ASSEMBLY_NAME}_genomic.gff.gz|the gene models: parsed by step 3, and the --gff guide for Liftoff"
  "${ASSEMBLY}_${ASSEMBLY_NAME}_protein.faa.gz|${ASSEMBLY}|${RELEASE}|${BASE}/${ASSEMBLY}_${ASSEMBLY_NAME}_protein.faa.gz|the protein set: BUSCO --proteins, InterProScan, eggNOG-mapper"
  "${ASSEMBLY}_${ASSEMBLY_NAME}_cds_from_genomic.fna.gz|${ASSEMBLY}|${RELEASE}|${BASE}/${ASSEMBLY}_${ASSEMBLY_NAME}_cds_from_genomic.fna.gz|the CDS sequences: the start/stop-codon and coding-length diagnostics"
  "${ASSEMBLY}_${ASSEMBLY_NAME}_feature_table.txt.gz|${ASSEMBLY}|${RELEASE}|${BASE}/${ASSEMBLY}_${ASSEMBLY_NAME}_feature_table.txt.gz|the flat attribute table: the gene and transcript names"
  "${ASSEMBLY}_${ASSEMBLY_NAME}_genomic_gaps.txt.gz|${ASSEMBLY}|${RELEASE}|${BASE}/${ASSEMBLY}_${ASSEMBLY_NAME}_genomic_gaps.txt.gz|the gap positions: whether a model overlaps a gap in the assembly"
  "${ASSEMBLY}_${ASSEMBLY_NAME}_gene_ontology.gaf.gz|${ASSEMBLY}|${RELEASE}|${BASE}/${ASSEMBLY}_${ASSEMBLY_NAME}_gene_ontology.gaf.gz|the GO annotations: the GO half of the gene-to-term map for test T6"
  "${ASSEMBLY}_${ASSEMBLY_NAME}_assembly_report.txt|${ASSEMBLY}|${RELEASE}|${BASE}/${ASSEMBLY}_${ASSEMBLY_NAME}_assembly_report.txt|the sequence-to-assembly mapping, and the file stating both accessions"
  "${ASSEMBLY}_${ASSEMBLY_NAME}_feature_count.txt.gz|${ASSEMBLY}|${RELEASE}|${BASE}/${ASSEMBLY}_${ASSEMBLY_NAME}_feature_count.txt.gz|NCBI's own counts of the annotation"
  "Aplysia_californica_AR102_annotation_report.xml|${ASSEMBLY}|${RELEASE}|${BASE}/Aplysia_californica_AR102_annotation_report.xml|the Release 102 annotation report"
  "README_Aplysia_californica_annotation_release_102|${ASSEMBLY}|${RELEASE}|${BASE}/README_Aplysia_californica_annotation_release_102|the release readme, which states the release strings"
  "new_unigenes.fasta|none|${TOOLS_2020}|${TOOLS_BASE}/new_unigenes.fasta|the 2020 merged-unigene build: 26,849 nucleotide sequences, a subset of the 2022 assembly that matches no published count. Not the analysis input"
  "annotation_1A-2C.fasta|${TSA}|${TOOLS_CNS}|${TOOLS_BASE}/annotation_1A-2C.fasta|the CNS set: 39,486 nucleotide sequences, the paper's final unigene set at a minimum ORF length of 400 bp, carrying the Trinotate product names. The analysis input"
  "current.annotation.fasta|none|${TOOLS_CURRENT}|${TOOLS_BASE}/current.annotation.fasta|AplysiaTools' live annotation: every tissue's nucleotide sequences in one file, of which the CNS subset is identical to annotation_1A-2C.fasta"
  "merged.unigenes.trinotate.longest_orf.json|none|${TOOLS_2020}|${TOOLS_BASE}/merged.unigenes.trinotate.longest_orf.json|the Trinotate functional annotation of the 2020 merged unigenes: product, Pfam and GO"
  "tsa.GJYY.1.fsa_nt.gz|${TSA}|${TRANSCRIPTOME}|${TSA_BASE}/tsa.GJYY.1.fsa_nt.gz|the Orvis 2022 CNS transcriptome as deposited: 68,308 transcripts, the paper's DN-Trinity arm. The citable accession and the independent check on the sequences, whose record count, base total and length extremes all match the publisher's published aggregates in stats.tsa.GJYY"
  "tsa.GJYY.1.gbff.gz|${TSA}|${TRANSCRIPTOME}|${TSA_BASE}/tsa.GJYY.1.gbff.gz|the Orvis 2022 CNS transcriptome in GenBank flatfile format: the sequences carry no gene models, and their DEFINITION lines carry the original Trinity and asmbl names, as do the FASTA headers. Two independent records of the same mapping"
  "tsa.GJYY.mstr.gbff.gz|${TSA}|${TRANSCRIPTOME}|${TSA_BASE}/tsa.GJYY.mstr.gbff.gz|the TSA master record: the deposition's own accession, version, BioProject, BioSample, SRA, dates and assembly method"
  "stats.tsa.GJYY|${TSA}|${TRANSCRIPTOME}|${TSA_BASE}/stats.tsa.GJYY|the publisher's own counts for the TSA project: sequences, bases, longest and shortest"
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
  printf 'file\taccession\tannotation_release\turl\tbytes\tmd5\tmd5_source\tsha256\tpurpose\n'
  for ROW in "${ROWS[@]}"; do
    FILE="${ROW%%|*}"
    REST="${ROW#*|}"
    ACCESSION="${REST%%|*}"
    REST="${REST#*|}"
    ANNOTATION_RELEASE="${REST%%|*}"
    REST="${REST#*|}"
    URL="${REST%%|*}"
    PURPOSE="${REST#*|}"
    TARGET="${RAW}/${FILE}"
    BYTES="$(stat -c%s "$TARGET")"
    SHA256="$(sha256sum "$TARGET" | awk '{print $1}')"
    PUBLISHED="$(awk -v file="$FILE" '{n=$2; sub(/^.*\//,"",n); if (n==file) print $1}' "${RAW}/md5checksums.txt" 2>/dev/null || true)"
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
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
      "$FILE" "$ACCESSION" "$ANNOTATION_RELEASE" "$URL" "$BYTES" "$MD5" "$SOURCE" "$SHA256" "$PURPOSE"
  done
} > "${OUT}.new"

mv "${OUT}.new" "${OUT}"
echo "==> wrote ${OUT} with $((${#ROWS[@]})) files"
