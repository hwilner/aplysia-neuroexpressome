# P01-02.4 — the checksum manifest

**Subtask:** P01-02.4 — record the SHA-256 of every downloaded file in `data/manifest.tsv`.
**Status:** complete.
**Date:** 2026-11-14.

## What this is

`data/raw/` is gitignored. The bytes of the inputs are not in the repository, and
they are not meant to be — the inputs are re-fetchable from NCBI, and a 240 MB
assembly has no business in a Git history. That leaves a gap: without a record
of the checksums, the repository says *which* inputs were used but not *which
bytes* of them.

`data/manifest.tsv` closes that gap. It is committed; the data is not.

| | |
|---|---|
| Path | `data/manifest.tsv` |
| Generator | `scripts/make_manifest.sh` |
| Tests | `tests/test_data_manifest.py` (15 tests) |
| Rows | 12 files |
| Tracked | yes — only `data/raw/` and `data/derived/` are ignored |

## The columns

| Column | Meaning |
|---|---|
| `file` | the name of the file, as it sits in `data/raw/` |
| `assembly` | the RefSeq accession the file belongs to (`GCF_000002075.1`) |
| `annotation_release` | the NCBI release the file belongs to |
| `url` | where it was fetched from |
| `bytes` | its size |
| `md5` | the MD5 NCBI publishes, where it publishes one |
| `md5_source` | whether that MD5 is published, or was not available |
| `sha256` | the SHA-256, computed here |
| `purpose` | what the pre-registration uses it for |

The two release columns say which release a file belongs to, which is what
anchors a checksum. They are **not** the verbatim release strings: that is
P01-02.5, and it is a separate artefact.

## The files

| File | Bytes | MD5 | SHA-256 |
|---|---|---|---|
| `md5checksums.txt` | 3,825 | — | `c4f58b70…` |
| `GCF_000002075.1_AplCal3.0_genomic.fna.gz` | 240,027,920 | published | `be3fa26b…` |
| `GCF_000002075.1_AplCal3.0_genomic.gff.gz` | 10,397,752 | published | `d1f21200…` |
| `GCF_000002075.1_AplCal3.0_protein.faa.gz` | 8,374,587 | published | `b7823835…` |
| `GCF_000002075.1_AplCal3.0_cds_from_genomic.fna.gz` | 12,854,865 | published | `2f44bede…` |
| `GCF_000002075.1_AplCal3.0_feature_table.txt.gz` | 1,869,581 | published | `d4d0da94…` |
| `GCF_000002075.1_AplCal3.0_genomic_gaps.txt.gz` | 1,650,620 | published | `6363cdb7…` |
| `GCF_000002075.1_AplCal3.0_gene_ontology.gaf.gz` | 600,653 | published | `8e97efed…` |
| `GCF_000002075.1_AplCal3.0_assembly_report.txt` | 408,931 | published | `684e3834…` |
| `GCF_000002075.1_AplCal3.0_feature_count.txt.gz` | 477 | published | `fbe02746…` |
| `Aplysia_californica_AR102_annotation_report.xml` | 162,865 | — | `87510054…` |
| `README_Aplysia_californica_annotation_release_102` | 719 | — | `c4f58b70…` |

The full values are in the manifest itself; the table above truncates them.

`md5checksums.txt` is NCBI's own checksum list for the assembly directory. It is
in the manifest because the manifest's `md5` column is taken from it, and a file
that a checksum column depends on belongs in the checksum record.

**Three files have no published MD5**: the two release-document files, which
NCBI does not checksum, and `md5checksums.txt`, which cannot list itself. Their
`md5_source` reads `none published` — it does not read `published by NCBI`, and
it does not read like a file that was checked against the publisher.

## How to check the inputs against the manifest

From the repository root, with the inputs fetched:

```bash
cd data/raw
awk -F'\t' 'NR>1{print $8"  "$1}' ../manifest.tsv | sha256sum -c -
```

This reports `OK` for each of the twelve files, and `FAILED` for any file whose
bytes have changed. It was checked in both directions: the manifest passes as
written, and appending a byte to a file turns it into a `FAILED`.

To regenerate the manifest from scratch — after a re-fetch, or if the input set
changes:

```bash
scripts/make_manifest.sh
```

The script fails rather than writing a manifest that is quietly short of a file.
That matters: a manifest missing one row reads like a complete manifest, and the
row it omits is exactly the one nobody checks.

## What the tests hold together

`tests/test_data_manifest.py` checks the manifest against three things, because
three artefacts can disagree and only one of them is checked by hand:

1. **The files on disk.** Size, SHA-256, and MD5 recomputed and compared. Skipped
   where the inputs are absent, which is continuous integration by design.
2. **The two download notes.** `P01-02-2-assembly-download.md` and
   `P01-02-3-annotation-download.md` record the same checksums in prose. The
   test requires that every checksum in a note appears in the manifest with the
   same value, and that the manifest's assembly checksum equals the assembly
   note's. These checks always run: both sides are committed, so a disagreement
   between them would otherwise go unnoticed.
3. **NCBI's published checksums.** For the files that have one, the MD5 column
   must match the file's actual MD5.

Two further tests are worth naming. The manifest is checked to be **not
gitignored** — if a future edit to `.gitignore` swallowed it, the inputs would
have no committed record at all, and that is the failure this whole artefact
exists to prevent. And the set of files in `data/raw/` is checked against the set
of rows in the manifest, in both directions, so an input that arrives without
being recorded is caught.

## Note on naming

`tests/test_data_manifest.py` is this file's test suite. `tests/test_manifest.py`
is the older suite from P01-01.x, which tests the *tool* manifest — the packages
and their versions inside the container image. Two different manifests, two
different files; they were briefly conflated and the names now say which is
which.
