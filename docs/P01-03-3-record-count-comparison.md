# P01-03.3 — the record counts, side by side

**Subtask:** P01-03.3 — compare record counts between the two transcriptome sources.
**Status:** complete.
**Date:** 2026-11-22.

> **Corrected 2026-11-24.** This note called AplysiaTools' 39,486-record
> file the **CNS protein set**. It is nucleotide — every residue is A, C, G or
> T — and so is every other transcriptome file AplysiaTools publishes, which
> means there is no protein set there to obtain. The counts, the overlaps and
> the derivation in this note are unaffected; only the word was wrong. The
> consequence is deviation **D005** (issue #32). See
> `docs/P01-03-4-sequence-sampling.md`.


## The question the pre-registration asks

§3.2, step 1 of `materials-and-methods.md`:

> Obtain the merged-unigene FASTA and predicted protein set from AplysiaTools;
> obtain the Orvis 2022 assembly from GenBank. Confirm the two are the same
> underlying build by comparing sequence counts and a random sample of 50
> sequences.

This note is the counting half of that instruction. It does not assume the
counts agree. It counts each file, says what each count is a count *of*, and
puts them side by side, so that the agreement — or the absence of it — is
visible.

**The counts do not agree, and the reason is not arithmetic. AplysiaTools is
not one build.** It is a directory of files from four different years, and the
two the pre-registration names are from 2020 and 2021, while the Orvis 2022
assembly was deposited in June 2022. The merged-unigene FASTA and the Orvis
transcriptome are not two copies of one build. They are two builds.

## The counts

Every number below is computed by `scripts/compare_transcriptome_counts.py`
from the downloaded files and written to `data/derived/transcriptome_counts.tsv`.

| Source | File | Date | Records | Distinct unigenes | What it counts |
|---|---|---|---|---|---|
| GenBank TSA `GJYY00000000` | `tsa.GJYY.1.fsa_nt.gz` | 2022-06-10 | **68,308** | 68,308 | the Orvis 2022 CNS transcriptome: one record per unigene |
| AplysiaTools CNS set | `annotation_1A-2C.fasta` | 2021-04-28 | **39,486** | 39,486 | one nucleotide sequence per unigene of the CNS transcriptome |
| AplysiaTools merged unigenes | `new_unigenes.fasta` | 2020-11-11 | **26,849** | 26,849 | the merged-unigene nucleotide FASTA: one sequence per unigene |
| AplysiaTools merged unigenes, annotated | `merged.unigenes.trinotate.longest_orf.json` | 2020-11-11 | 24,339 | 24,339 | the Trinotate annotation of those 26,849 |
| AplysiaTools current annotation | `current.annotation.fasta` | 2025-07-15 | **196,953** | 174,400 | seven tissues' sequences in one file |
| AplysiaTools per-tissue unigenes | `/unigenes/`, six files | 2023-02-10 | **157,467** | 139,303 | one file per tissue, six tissues |

The dates are the servers' own `Last-Modified` headers, not an inference. They
are recorded in `data/derived/tissue_unigenes_sha256.tsv` for the per-tissue
files and were read directly for the `/data/` files.

## The paper's own numbers, for comparison

Orvis et al. (2022) publish four counts. The script carries them, so that the
comparison is against the source's numbers and not only against ours.

| The paper says | Count | Which file it is |
|---|---|---|
| clusters | 71,104 | no AplysiaTools file has this count |
| *"We refer to this set of 68,308 transcripts as 'unigenes'"* | 68,308 | **the GenBank TSA**, exactly |
| unigenes with a minimum ORF length of 400 bp | 39,486 | **the AplysiaTools CNS set**, exactly |
| transcripts after filtering for those shorter than 400 bp | 38,125 | no AplysiaTools file has this count |

Two of the four land exactly on a file we hold, and they are different files.
The 68,308 is the full unigene set, before the ORF filter; the 39,486 is that
set after it. The AplysiaTools CNS set *is* the paper's final set, one
sequence per unigene.

## The overlaps

From `data/derived/transcriptome_overlaps.tsv`:

| Left | Right | Shared | Share of left | Share of right |
|---|---|---|---|---|
| CNS set | TSA original names | **38,129** | 96.6% | 55.8% |
| merged unigenes | TSA original names | **12,551** | 46.7% | 18.4% |
| merged unigenes | CNS set | 8,089 | 30.1% | 20.5% |
| merged unigenes | current annotation | 9,826 | 36.6% | 5.6% |
| CNS set | current annotation, CNS set | **39,486** | 100.0% | 100.0% |
| per-tissue unigenes | current annotation, non-CNS records | **139,303** | 100.0% | 100.0% |

Two rows are exact identities and two more are near-exact:

- **The CNS set *is* the CNS set of the current annotation** — the same
  39,486 identifiers, every one of them.
- **The current annotation decomposes exactly**: its CNS set is 39,486 records
  and the six per-tissue files are 157,467, and 39,486 + 157,467 = 196,953,
  which is the number of records the file holds.
- **The six per-tissue files' union is exactly the set of distinct unigenes in
  the current annotation's non-CNS records** — 139,303 on both sides, the same
  set and not merely the same size.
- **Every one of the 13,314 `asmbl_` identifiers in the CNS set is in
  the TSA.** Not "most of them" — all of them.

The current annotation's 174,400 distinct unigenes are 39,486 under CNS and
139,303 under the other six tissues, less the **4,389** that occur under CNS
and another tissue both: 39,486 + 139,303 − 4,389 = 174,400.

## What `current.annotation.fasta` is made of

This was not in the pre-registration and it is now settled. The file is seven
tissue sets, and the six non-CNS ones are the per-tissue files, one for one:

| Tissue | Per-tissue file | Records | In `current.annotation.fasta` as |
|---|---|---|---|
| salivary | `A2.…unigenes.fasta` | 19,329 | `salivary.` |
| digestive | `A3.…unigenes.fasta` | 26,153 | `digestive.` |
| hepatopancreas | `A5.…unigenes.fasta` | 25,819 | `hepatopancreas.` |
| heart | `A7.…unigenes.fasta` | 25,467 | `heart.` |
| muscle | `A8.…unigenes.fasta` | 32,933 | `muscle.` |
| hermaphroditic | `A10.…unigenes.fasta` | 27,766 | `gills.` |
| CNS | — | 39,486 | `CNS.` |

Each count matches exactly. Note the one naming change: AplysiaTools calls
A10 `hermaphroditic` in the file name and `gills` in the current annotation.

**15,926 unigenes occur in more than one tissue**, and 4,389 of the
per-tissue unigenes are also in the CNS set — those are the ones the current
annotation files under a CNS prefix and a tissue prefix both.

## The trap: two identifier conventions

AplysiaTools writes tissue-prefixed identifiers in `current.annotation.fasta`
and in the per-tissue files — `salivary.asmbl_100`, `CNS.asmbl_340921` — and
bare identifiers in the merged-unigene FASTA and in the CNS set:
`asmbl_100`, `TRINITY_DN69529_c0_g1_i1`. The GenBank TSA carries the bare form
in its DEFINITION lines, which is the bridge P01-03.2 built. (P01-03.4 found
that the FASTA's own headers carry the same names, so the flatfile is the
second record of the mapping rather than the only one.)

Compared without removing the prefix, the six per-tissue sets look **disjoint
from each other** — 157,467 records, 157,467 distinct identifiers, nothing
shared. That is an artefact. With the prefix removed they share **15,926**
unigenes, and the current annotation shows the same structure: `asmbl_10004`
appears under both `hepatopancreas.` and `salivary.`, in the per-tissue files
and in the current annotation alike.

Every overlap number in this note is computed on the bare identifiers. A
comparison that forgets the prefix finds nothing, and a comparison that
reports "nothing in common" would be wrong.

## Why the two sources disagree

**They are different vintages, and the file dates say so.** The merged-unigene
FASTA is from 11 November 2020; the CNS set from 28 April 2021; the
Orvis 2022 assembly was deposited on 10 June 2022; the per-tissue files from
February 2023; the current annotation from July 2025. Four builds, four
years, one directory.

**They are built on different unigene populations.** The `asmbl_` identifier
namespace dominates one and not the others:

| Source | `asmbl_` | `TRINITY_DN` |
|---|---|---|
| merged unigenes (`new_unigenes.fasta`) | **24,099** (89.8%) | 2,750 |
| CNS set (`annotation_1A-2C.fasta`) | 13,314 (33.7%) | **26,172** |
| TSA original names | 23,003 (33.7%) | **45,305** |

**But they share the assembly generation.** The numeric ranges of the `asmbl_`
identifiers are essentially the same in all three — 1–341,054, 40–341,049 and
7–341,053 — so these are not two unrelated assemblies. They are two different
selections from the same assembly, taken at different times.

That is the shape of it: the merged-unigene file and the CNS set draw
on one assembly, and the merged-unigene file was built first, from a selection
that the CNS set does not contain. Of the merged file's 24,099 `asmbl_`
identifiers, **10,458 are in the TSA and 13,641 are not**.

## What follows

**The pre-registered instruction cannot be satisfied as written.** §3.2 step 1
asks that the merged-unigene FASTA and the Orvis 2022 assembly be confirmed to
be the same underlying build. They are not the same build, and no comparison
of counts or of 50 sampled sequences will make them so. This is filed as a
deviation, issue [#30], for the researcher to decide; the pre-registration has
not been edited.

**The pair that does correspond is the CNS set and the TSA.** Its count
is the paper's final count, and 38,129 of its 39,486 identifiers — including
all 13,314 of its `asmbl_` identifiers — are in the Orvis 2022 transcriptome.

That is what P01-03.4 and P01-03.5 should work on. P01-03.4's "extract 50
random sequences and confirm they are identical" is a test that **can** succeed
for the CNS set against the TSA, at the level of the underlying
transcripts; it cannot succeed for the merged-unigene FASTA, and running it
against that file would produce a negative result that says more about the
2020 build than about the data.

**Which build is authoritative** is P01-03.5's decision, and the evidence
points one way: the TSA and the CNS set describe the same
transcriptome, at two levels of processing, and the merged-unigene FASTA
describes an earlier one.

## Two limits that carry forward

**The TSA carries no gene models.** Its flatfile has 68,308 `source` features
and nothing else. Gene models for the lift-off have to come from the CNS
set or from the assembly, not from the TSA.

**The paper's 400 bp filter is on ORFs, not on transcripts.** 60,173 of the
TSA's 68,308 sequences are at least 400 nucleotides long, so the 39,486 cannot
be reproduced, or checked, from sequence lengths alone. Any count comparison
has to say which definition it is using, which is why the table above names
what each count is a count of.

## How to check

```bash
python3 scripts/fetch_tissue_unigenes.py     # six per-tissue files -> identifiers and checksums
python3 scripts/extract_tsa_names.py         # the TSA accession -> original-name bridge
python3 scripts/compare_transcriptome_counts.py
```

The last one writes `data/derived/transcriptome_counts.tsv` and
`data/derived/transcriptome_overlaps.tsv` and prints the table above. It
needs the downloaded files; without them it says which are missing rather than
reporting zeros.

The tests are `tests/test_transcriptome_counts.py`. They assert the counts
and the overlaps above, so a later change to the data cannot quietly move a
number.

## Note on the manifest

The six per-tissue FASTAs are **not** in `data/manifest.tsv` and their bytes
are not kept: they are 321 MB of input, not a result, and the comparison needs
their identifiers and their counts rather than their sequences. Their SHA-256
is recorded in `data/derived/tissue_unigenes_sha256.tsv`, and
`scripts/fetch_tissue_unigenes.py` recomputes it on every run and fails on a
mismatch. The AplysiaTools publisher serves no checksum for any of its files,
so that file is this repository's own record of the bytes that were counted.

The four `/data/` files and the four GenBank files stay in `data/manifest.tsv`,
where `scripts/fetch_transcriptomes.sh` checks them.
