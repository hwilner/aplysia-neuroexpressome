# P01-02.2 — the AplCal3.0 assembly FASTA

**Subtask:** P01-02.2 — download the AplCal3.0 assembly FASTA.
**Status:** complete.
**Date:** 2026-11-10.

## What was fetched

| | |
|---|---|
| File | `GCF_000002075.1_AplCal3.0_genomic.fna.gz` |
| Assembly | AplCal3.0 |
| RefSeq accession | `GCF_000002075.1` |
| GenBank accession | `GCA_000002075.2` |
| URL | `https://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/000/002/075/GCF_000002075.1_AplCal3.0/GCF_000002075.1_AplCal3.0_genomic.fna.gz` |
| Size | 240,027,920 bytes |
| MD5 | `fd012bb43298223de48b4ba0bccf54f3` |
| SHA-256 | `be3fa26b4b0ac9a2377354bf69591465935c7a6e1523b6ecd65890381f0cd844` |
| Fetched | 2026-11-10 |

It is in `data/raw/`, which is gitignored, and it is not committed. It is
re-fetchable from the accession above, and the fetch is scripted, so what
matters — the version — is recorded rather than the bytes.

## The accession in the pre-registration does not resolve

`materials-and-methods.md` §2.1 names the genome assembly as
**`GCF_000002075.2`**. That accession does not exist.

```
GCF_000002075.2   →  the RefSeq prefix with the GenBank version number
GCA_000002075.2   →  the GenBank accession, which does exist
GCF_000002075.1   →  the RefSeq accession, which does exist
```

The assembly itself is not in doubt. AplCal3.0 is one assembly, submitted by
the Broad Institute on 2013-05-15, and its RefSeq and GenBank copies carry
identical statistics: 4,331 scaffolds, scaffold N50 917,541. What is wrong is
the string in the pre-registration, which pairs the RefSeq prefix with the
GenBank version number.

Four independent sources agree that the RefSeq accession is
`GCF_000002075.1`:

- the **assembly report** inside the download itself, which states both
  accessions on consecutive lines — `# GenBank assembly accession:
  GCA_000002075.2` and `# RefSeq assembly accession: GCF_000002075.1`;
- **NCBI's annotation release readme** for Release 102, which lists
  `ASSEMBLY ACCESSION: GCF_000002075.1`;
- the **assembly record** in NCBI's own database, whose `assemblyaccession`
  field is `GCF_000002075.1` and whose name is `AplCal3.0`;
- the **file path**, which is
  `.../GCF/000/002/075/GCF_000002075.1_AplCal3.0/`. The `.2` directory
  returns HTTP 404.

The extended introduction already links the GenBank accession,
`GCA_000002075.2`, and that link resolves. So the repository carried the
right accession in one file and an unresolvable one in another.

**What was done:** the assembly the pre-registration unambiguously names —
AplCal3.0, the 2013 Broad Institute assembly, RefSeq Annotation Release 102
— was downloaded, from its RefSeq accession. The pre-registration has not
been edited. The discrepancy is logged as a deviation issue for a decision,
the same way the InterProScan data-release change was handled.

## How it was verified

Three checks, each catching something the others do not.

1. **MD5 against the checksum NCBI publishes.** The publisher's own
   `md5checksums.txt` gives
   `fd012bb43298223de48b4ba0bccf54f3` for this file, and the download
   matches it. This catches a truncated or corrupted transfer.
2. **`gzip -t`.** The file is complete by its length but could still be
   corrupt inside; this catches that.
3. **SHA-256.** Recorded above for the checksum manifest, which is
   `data/manifest.tsv` and is written in P01-02.4.

The content was then checked rather than assumed:

| | |
|---|---|
| Sequences | 4,332 |
| Nuclear scaffolds | 4,331 |
| Plus | 1 mitochondrion, `NC_005827.1` |
| Total bases | 927,310,431 |
| Scaffold N50 | 917,541 |

Every sequence header carries `AplCal3.0`, so the file identifies itself as
the assembly it is supposed to be:

```
>NW_004797271.1 Aplysia californica isolate F4 #8 unplaced genomic scaffold,
AplCal3.0 scaffold00001, whole genome shotgun sequencing project AASC03
```

## The assembly, from its own report

```
# Assembly name:  AplCal3.0
# Organism name:  Aplysia californica (California sea hare)
# Isolate:  F4 #8
# Sex:  hermaphrodite
# Taxid:          6500
# BioSample:      SAMN02953658
# BioProject:     PRJNA13635
# Submitter:      Broad Institute
# Date:           2013-05-15
# Assembly type:  haploid
# Release type:   major
# Assembly level: Scaffold
# Genome representation: full
# WGS project:    AASC03
# Assembly method: allpaths v. R40582
# Genome coverage: 66x
# Sequencing technology: Illumina Hi-Seq
```

The annotation that goes with this assembly is NCBI Aplysia californica
Annotation Release 102: evidence freeze 18-August-2020, release date
31-August-2020. It is fetched in P01-02.3.

## How to fetch it again

```bash
scripts/fetch_assembly.sh            # into data/raw/
scripts/fetch_assembly.sh /somewhere # somewhere else
```

The script downloads the file if it is not already there, verifies it
against NCBI's published MD5, checks the gzip, and prints the size and the
SHA-256. Run it twice and the second run verifies rather than re-downloads,
so it is safe to run in a pipeline.

## What is not committed

The 240 MB FASTA is not committed, and neither is the checksum list beside
it. `data/raw/` is gitignored, for the reason given in
[`P01-02-1-data-layout.md`](P01-02-1-data-layout.md): the inputs are large
and re-fetchable, and they are versioned by the SHA-256 in
`data/manifest.tsv` rather than by committing the bytes.

## What comes next

| subtask | what it does |
|---|---|
| P01-02.3 | downloads the RefSeq Release 102 annotation and its supporting files |
| P01-02.4 | records the SHA-256 of every file in `data/manifest.tsv` |
| P01-02.5 | captures the assembly and annotation release strings verbatim |

## Files

| file | what it is |
|---|---|
| `scripts/fetch_assembly.sh` | the fetch, and the verification of it |
| `data/raw/GCF_000002075.1_AplCal3.0_genomic.fna.gz` | the assembly; gitignored, not committed |
| `data/raw/md5checksums.txt` | NCBI's published checksums for the assembly directory |
| `docs/P01-02-2-assembly-download.md` | this note |
