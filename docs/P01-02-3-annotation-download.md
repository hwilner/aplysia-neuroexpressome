# P01-02.3 — the RefSeq Release 102 annotation

**Subtask:** P01-02.3 — download the RefSeq Annotation Release 102 and its supporting files.
**Status:** complete.
**Date:** 2026-11-12.

## What was fetched

All from `GCF_000002075.1_AplCal3.0`, the RefSeq accession for AplCal3.0, as described in
[`P01-02-2-assembly-download.md`](P01-02-2-assembly-download.md).

| File | Bytes | What it is |
|---|---|---|
| `GCF_000002075.1_AplCal3.0_genomic.gff.gz` | 10,397,752 | the gene models |
| `GCF_000002075.1_AplCal3.0_protein.faa.gz` | 8,374,587 | the protein set |
| `GCF_000002075.1_AplCal3.0_cds_from_genomic.fna.gz` | 12,854,865 | the CDS sequences |
| `GCF_000002075.1_AplCal3.0_feature_table.txt.gz` | 1,869,581 | the flat attribute table |
| `GCF_000002075.1_AplCal3.0_genomic_gaps.txt.gz` | 1,650,620 | the gap positions |
| `GCF_000002075.1_AplCal3.0_gene_ontology.gaf.gz` | 600,653 | the GO annotations |
| `GCF_000002075.1_AplCal3.0_assembly_report.txt` | 408,931 | the sequence mapping |
| `GCF_000002075.1_AplCal3.0_feature_count.txt.gz` | 477 | NCBI's own counts |
| `Aplysia_californica_AR102_annotation_report.xml` | 162,865 | the Release 102 report |
| `README_Aplysia_californica_annotation_release_102` | 719 | the release readme |

| File | SHA-256 | Verified against |
|---|---|---|
| `GCF_000002075.1_AplCal3.0_genomic.gff.gz` | `d1f21200d3a87a958eed12c4b56eda68e3a6bd392e1b89ecf8dbb0f6cc233396` | NCBI's published MD5 |
| `GCF_000002075.1_AplCal3.0_protein.faa.gz` | `b78238359ca5cf689fc851e900fcdd3ab70564960817c166daddcff4993f427d` | NCBI's published MD5 |
| `GCF_000002075.1_AplCal3.0_cds_from_genomic.fna.gz` | `2f44bede065f74534826d46f185ae8ff4b216fba8b50d2b8cfab8fc36f2abb84` | NCBI's published MD5 |
| `GCF_000002075.1_AplCal3.0_feature_table.txt.gz` | `d4d0da94885e7b1db6674a82dc7f6e2c3760243d89c9c0fda168faac8f52e7c3` | NCBI's published MD5 |
| `GCF_000002075.1_AplCal3.0_genomic_gaps.txt.gz` | `6363cdb706fc97fb871024210fbeadac7ac11f3a024b6345f74e54f95ac0c73a` | NCBI's published MD5 |
| `GCF_000002075.1_AplCal3.0_gene_ontology.gaf.gz` | `8e97efed2ac1215acd56ed5c9a371252368099810a412a9c8c7ac5016b1c96bd` | NCBI's published MD5 |
| `GCF_000002075.1_AplCal3.0_assembly_report.txt` | `684e383469caaede8528e70ef2db993087d1467041df3e4ca2020b31482851fc` | NCBI's published MD5 |
| `GCF_000002075.1_AplCal3.0_feature_count.txt.gz` | `fbe02746976005ff94cb53a87b591a93b6553a27f3274f7f4c23be155fccbbd9` | NCBI's published MD5 |
| `Aplysia_californica_AR102_annotation_report.xml` | `875100545cedbcc21f6c589fb95bbbd71b3be5d864ffe04bc4d0db2a95f6183f` | integrity and SHA-256 only — no published checksum |
| `README_Aplysia_californica_annotation_release_102` | `c4f58b707b4f7e86b04dc3dbf257fec23827e9fd19f23d586cd7ff699d2d8d5b` | integrity and SHA-256 only — no published checksum |

The last two carry the release documentation rather than data, and NCBI publishes no checksum
for either. The script says so per file rather than implying a check it did not do.

None of this is committed. `data/raw/` is gitignored; the fetch is scripted, and what is
recorded is the version rather than the bytes.

## Which files, and why each one is here

Each is here because a pre-registered step consumes it.

| File | Consumed by |
|---|---|
| `genomic.gff.gz` | step 3, "parse the GFF"; and Liftoff, which takes it as the `--gff` guide |
| `protein.faa.gz` | step 2, BUSCO `--proteins` against the annotation's protein set; InterProScan and eggNOG-mapper read the same set |
| `cds_from_genomic.fna.gz` | step 3, the start/stop-codon and coding-length diagnostics |
| `feature_table.txt.gz` | the gene and transcript names, and the flat table the catalogue is built from |
| `genomic_gaps.txt.gz` | step 3, whether a model overlaps a gap in the assembly |
| `gene_ontology.gaf.gz` | the GO half of the gene-to-term map that test T6 is run against; the KEGG half comes from eggNOG-mapper |
| `assembly_report.txt` | the sequence-to-assembly mapping, and the file that states both accessions |
| `feature_count.txt.gz` | NCBI's own counts, for the record |

## What was deliberately not fetched

- **The GTF and the GenBank flat file.** The same annotation in other formats. The GFF3 is
  what step 3 parses and what Liftoff takes, and the flat file is 330 MB of the same
  information.
- **The Gnomon models** (`Gnomon_models/`) and the **evidence alignments**
  (`Evidence_alignments/`). The Gnomon models are NCBI's predictions; this project makes its
  own predictions and compares them with the annotation, so using theirs as well would blur
  the comparison. The evidence alignments are NCBI's own transcript-to-genome alignments;
  step 8 runs Liftoff, which is the alignment.

## What the annotation actually is

This is the part worth reading twice, because it bears on what the "before" arm means.

The GFF carries 612,340 feature lines. Its protein-coding gene features break down by
source like this:

| Source | Protein-coding genes | What it is |
|---|---|---|
| `Gnomon` | 19,142 | ab initio prediction by Gnomon |
| `BestRefSeq` | 216 | curated RefSeq models |
| `BestRefSeq,Gnomon` | 54 | RefSeq-supported models that were submitted to Gnomon |
| `RefSeq` | 13 | the mitochondrion |
| **Total** | **19,425** | which is NCBI's own "Placements" count for protein-coding genes |

The protein set says the same thing in a different way. `protein.faa.gz` holds 26,656
sequences: **26,391 with `XP_` accessions** (Gnomon-predicted), 252 with `NP_` (curated
RefSeq) and 13 with `YP_` (the mitochondrion).

**So the annotation named in §2.1 as the "Current reference annotation" and the "before" arm
is about 98.6% machine-predicted gene models.** Only 283 of the 19,425 protein-coding gene
placements are RefSeq-supported. The rest are Gnomon predictions that NCBI released
alongside the curated set.

This is not a deviation. The pre-registration names Release 102, and Release 102 is what
was fetched. But it changes what the baseline arm is: Gate G1 asks whether baseline BUSCO
completeness is at least 90%, and that measurement is being taken against a mostly
predicted annotation rather than a curated one. The methods must say so, and the comparison
against the repaired models must be read with it in view — the lift-off's advantage over
the baseline is a comparison against predictions, not against curated gene models.

The Release 102 report records where the models came from: 12,764 and 6,075 annotation
models were passed to Gnomon in two categories, with mean identities of 57.1% and 70.0%
and mean coverages of 39.4% and 68.8% to the supporting RNA-seq alignments.

The rest of the annotation, for completeness:

| | |
|---|---|
| mRNA | 26,644 |
| CDS with protein | 26,656 unique ids, 26,676 placements |
| lncRNA genes | 1,406 |
| tRNA genes | 399 |
| pseudogenes | 68 |
| snRNA / snoRNA / rRNA / misc / guide | 66 / 110 / 28 / 26 / 3 |
| GO annotation lines | 56,576, across `enables`, `involved_in`, `located_in` and `part_of` |
| Gaps in the assembly | 160,212 intervals, each typed and with its linkage evidence |

## How it was verified

The same three checks as the assembly: the MD5 against the checksum NCBI publishes, where
there is one; `gzip -t` for integrity; and the SHA-256 for the manifest. The content was
then read back rather than assumed — the feature counts above were counted from the files,
and they reconcile with NCBI's own `feature_count.txt.gz`.

The AR102 report independently confirms the accession, stating
`<Accession>GCF_000002075.1</Accession>` and `<Name>AplCal3.0</Name>`, which is the fifth
source to give that accession since P01-02.2.

## How to fetch it again

```bash
scripts/fetch_annotation.sh            # into data/raw/
scripts/fetch_annotation.sh /somewhere # somewhere else
```

The script downloads what is missing, verifies what is present, and is safe to run twice.

## What comes next

| subtask | what it does |
|---|---|
| P01-02.4 | records the SHA-256 of every file in `data/manifest.tsv` |
| P01-02.5 | captures the assembly and annotation release strings verbatim |

## Files

| file | what it is |
|---|---|
| `scripts/fetch_annotation.sh` | the fetch, and the verification of it |
| `data/raw/` | the annotation and its supporting files; gitignored, not committed |
| `docs/P01-02-3-annotation-download.md` | this note |
