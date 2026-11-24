# P01-03.1 — the AplysiaTools transcriptomes

**Subtask:** P01-03.1 — download the AplysiaTools merged-unigene FASTA.
**Status:** complete.
**Date:** 2026-11-18.

> **Corrected 2026-11-24.** This note called `annotation_1A-2C.fasta` and
> `current.annotation.fasta` **protein** sets. They are not. Every residue in
> all 39,486 records of the first and all 196,953 records of the second is A,
> C, G or T — there is not one amino-acid letter in 500 megabases of sequence.
> The counts, the overlaps and the identifiers in this note are unaffected;
> only the word was wrong. The consequence is not cosmetic, and it is the
> reason the correction is banner-ed rather than quietly edited: AplysiaTools
> publishes **no protein sequences at all**, so the "predicted protein set"
> that §3.2 step 1 asks for cannot be obtained there and has to be derived
> locally by P01-10.1. That is deviation **D005** (issue #32). See
> `docs/P01-03-4-sequence-sampling.md`.


## What was fetched

Four files from `http://aplysiatools.org/data/`.

| File | Bytes | What it is | Server's Last-Modified |
|---|---|---|---|
| `new_unigenes.fasta` | 96,749,623 | the merged-unigene **nucleotide** FASTA | 2020-11-11 |
| `annotation_1A-2C.fasta` | 97,345,806 | the **CNS** set: one nucleotide sequence per unigene, with predicted product names | 2021-04-28 |
| `current.annotation.fasta` | 427,357,077 | the live **current** annotation: every tissue's sequences in one file | 2025-07-15 |
| `merged.unigenes.trinotate.longest_orf.json` | 4,487,388 | the Trinotate functional annotation of the merged unigenes | 2020-11-11 |

SHA-256 for all four is in `data/manifest.tsv`, along with the URL each came
from and what it is for. The raw files stay uncommitted and are re-fetched by
`scripts/fetch_transcriptomes.sh`.

## Where the files actually are

The obvious route is a dead end, and it is worth recording why.

AplysiaTools' homepage is a plain static site. Its "Transcriptome Blast" page
is three lines of HTML pointing at `http://aplysiatools.org:4567/`, which is a
**SequenceServer** 1.0.14 instance — a BLAST frontend. SequenceServer lists 21
databases there, including `Unigenes, all tissues, merged clusters` and its
protein twin `Unigenes, all tissues merged clusters (predicted ORFs)`, and the
practice document on the site tells a user to tick *"00 unigenes merged"* and
BLAST a sequence against it.

None of that gets you a file. SequenceServer serves **hits**, not databases:
its only file route is `get_sequence/?sequence_ids=…&database_ids=…`, which
returns one sequence at a time, and there is no route that returns a whole
database. `/databases`, `/datasets`, `/dataset/<id>` and every other guess all
return 404 — the app exposes `/` and the AJAX endpoints and nothing else.

The files are on the **web** server, not behind the BLAST form:
`http://aplysiatools.org/data/` is an Apache directory listing, and
`http://aplysiatools.org/unigenes/` is another. That is where all four files
came from.

## The counts do not agree

This is the finding of the subtask, and it is the reason P01-03.3 to P01-03.5
exist rather than being housekeeping.

The paper (Orvis et al. 2022, *PNAS* 119:e2122301119) reports, in Fig. 1A:

> The combined 159,559 contigs were clustered based on ORFs with CD-HIT, and
> the longest ORF per cluster was identified as the unigene, yielding 71,104,
> which reduced to 39,486 unigenes with a minimum ORF length of 400 bp.

and, separately, for the DN-Trinity-only comparison arm:

> We refer to this set of 68,308 transcripts as "unigenes," or 38,125
> transcripts after filtering for those shorter than 400 bp.

What the files actually contain:

| Source | Records |
|---|---|
| `new_unigenes.fasta` | **26,849** nucleotide sequences (94,756,984 nt; min 297, median 2,366, max 48,455) |
| `annotation_1A-2C.fasta` | **39,486** nucleotide sequences |
| `current.annotation.fasta`, CNS subset | **39,486** nucleotide sequences |
| `current.annotation.fasta`, all tissues | **196,953** nucleotide sequences |
| `merged.unigenes.trinotate.longest_orf.json` | **24,339** annotated unigenes |

**39,486 is exactly the paper's final count.** The CNS set is the
paper's unigene set, one sequence per unigene.

But the nucleotide file does not agree with it. Of `new_unigenes.fasta`'s
26,849 identifiers, only **8,089** appear in the 39,486-sequence CNS set; 9,826
appear anywhere in the 196,953-sequence current annotation. The two files are
not the same sequence set, and they are not in a subset relationship.

So AplysiaTools publishes at least three different generations of the same
transcriptome, and the counts are:

| Generation | File | Count |
|---|---|---|
| merged unigenes, nucleotide | `new_unigenes.fasta` | 26,849 |
| the same, functionally annotated | `merged.unigenes.trinotate.longest_orf.json` | 24,339 |
| the paper's final unigene set, as nucleotide | `annotation_1A-2C.fasta` | 39,486 |

The Trinotate JSON annotates 24,339 of the 26,849 in `new_unigenes.fasta` —
the 2,510 that carry no annotation are the difference. That relationship is
exact: the JSON's identifiers are a subset of the FASTA's, and the TRINITY_DN
counts of the two are identical at 2,750 each.

## Two files that are the same set

`annotation_1A-2C.fasta` (2021) and the CNS subset of
`current.annotation.fasta` (2025) have **the same 39,486 identifiers and
100% identical sequences** — every one of the 39,486 was checked, not
a sample. The 2025 file is the same CNS set plus six other tissues:

| Tissue | Sequences |
|---|---|
| CNS | 39,486 |
| muscle | 32,933 |
| gills | 27,766 |
| digestive | 26,153 |
| hepatopancreas | 25,819 |
| heart | 25,467 |
| salivary | 19,329 |

So the CNS set the pre-registration asks for is available in two files and
does not need to be derived: `annotation_1A-2C.fasta` is it.

The naming is AplysiaTools' own and the paper does not explain it — "1A-2C"
and the `asmbl_` prefix appear nowhere in the paper or its abstract. The
identifier namespaces do, however, line up across files:

| File | `asmbl_*` | `TRINITY_DN*` |
|---|---|---|
| `new_unigenes.fasta` | 24,099 | 2,750 |
| `annotation_1A-2C.fasta` | 13,314 | 26,172 |
| Trinotate JSON | 21,589 | 2,750 |

`asmbl_` identifiers run `asmbl_1` to `asmbl_341,054` and are sparse — 26,849
of that range in `new_unigenes.fasta`. `TRINITY_DN…` identifiers are the
original de novo Trinity transcript names.

## There is no checksum to verify against

The publisher provides no MD5 and no SHA-256 for any of these files. NCBI
publishes `md5checksums.txt` for the assembly directory; AplysiaTools
publishes nothing.

So the record is this repository's own. `data/manifest.tsv` holds the SHA-256
of every file, and `scripts/fetch_transcriptomes.sh` recomputes it on every
run and compares it with the manifest — so a file that changes under us is
detected rather than silently accepted. The manifest is the claim; the script
checks it. The `md5_source` column for these rows reads `none published`,
which is what it is.

The server's `Last-Modified` headers are recorded in this note for the same
reason: `current.annotation.fasta` was last written on **15 July 2025**, five
years after the paper, so the "current" annotation is a moving target and its
checksum is the only way to say which version an analysis used.

## What was not fetched, and why

`http://aplysiatools.org/unigenes/` holds the six per-tissue unigene FASTAs
that the merged clusters were built from. They are recorded here with their
sizes and left alone: they are the inputs to the merge, not the merged
result, and P01-03.1 asks for the merged set.

| File | Bytes |
|---|---|
| `A2.transrate.good.longestorfs.p1.cdhitest.unigenes.fasta` | 27,528,901 |
| `A3.transrate.good.longestorfs.p1.cdhitest.unigenes.fasta` | 54,902,670 |
| `A5.transrate.good.longestorfs.p1.cdhitest.unigenes.fasta` | 52,749,566 |
| `A7.transrate.good.longestorfs.p1.cdhitest.unigenes.fasta` | 51,603,634 |
| `A8.transrate.good.longestorfs.p1.cdhitest.unigenes.fasta` | 71,753,403 |
| `A10.transrate.good.longestorfs.p1.cdhitest.unigenes.fasta` | 61,976,796 |

Also not fetched: `merged.unigenes.trinotate.xls` (64,515,953 bytes) and
`merged.unigenes.trinotate.longest_orf.xls` (28,823,379 bytes), which carry
the same Trinotate annotation as the JSON in a spreadsheet format. The JSON is
the smaller copy of the same thing and is what was taken.

## What the next subtasks have to settle

§3.2 step 1 asks for the merged-unigene FASTA **and** the predicted protein
set, then says: *"Confirm the two are the same underlying build by comparing
sequence counts and a random sample of 50 sequences."* The word **confirm**
assumes an answer. What the files show is that the two are *not* the same
sequence set — 8,089 shared identifiers out of 26,849 and 39,486 — so the
adjudication is real work, and P01-03.3, P01-03.4 and P01-03.5 have to decide
which build the analysis runs on.

The Orvis supplementary appendix anticipates exactly this:

> the assemblies on NCBI are continuing to evolve based on new sequences and
> new scaffolds; for example, the genomic sequences now available on BLAST
> include scaffolds and may be less fragmented than the original Broad genome
> that we analyzed, or than what is available on NCBI BLAST of WGS assemblies
> or available for download

So the three copies of the Orvis 2022 transcriptome — AplysiaTools'
`new_unigenes.fasta`, AplysiaTools' 39,486-sequence CNS set, and the GenBank TSA
`GJYY00000000` that P01-03.2 fetches — are three more instances of the same
problem, and the counts in this note are the starting evidence for resolving
it rather than a conclusion.

## How to check

```bash
scripts/fetch_transcriptomes.sh    # re-verifies all four against the manifest
python3 -m unittest discover -s tests
```

The fetch script is idempotent: it downloads what is absent, verifies what is
present, and does not re-download. It refuses to continue if a file's bytes
no longer match the manifest.

## Note on the manifest

Adding these four files changed the manifest's `assembly` column to
`accession`, because the transcriptome files belong to the GenBank TSA project
`GJYY00000000` and not to an assembly at all. A column that means one thing
for the genome files and another for the transcriptome files is a trap, and
the manifest is the record every later step reads.

## Addendum — P01-03.2, 2026-11-20

P01-03.2 fetched the third copy of this transcriptome, from GenBank TSA
`GJYY00000000`, and it changes which of the two AplysiaTools files is the
outlier.

The GenBank flatfile carries the original assembly names in its DEFINITION
lines, which is the bridge between the two identifier namespaces. With
it, the overlap is:

| AplysiaTools file | Its identifiers also in the TSA |
|---|---|
| CNS set (39,486) | **38,129** — 96.5% |
| `new_unigenes.fasta` (26,849) | **12,551** — 46.7% |

So the CNS set is very nearly the TSA's content, filtered down to the
paper's 39,486 — and **all 13,314** of its `asmbl_` identifiers are in the
TSA. The nucleotide file is the strange one: barely half of it is in the TSA
at all.

What this note recorded above still stands. The nucleotide file and the
CNS set are not the same sequence set, and only 8,089 identifiers are
shared between them. But the third copy shows that of the two, it is the
**nucleotide file** that is the odd one out, not the CNS set. P01-03.3
to P01-03.5 now have that much to work with.
