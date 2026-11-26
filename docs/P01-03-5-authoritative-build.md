# P01-03.5 — which build is authoritative, and the checksum for both

**Subtask:** P01-03.5 — record which build is authoritative, and checksum both.
**Status:** complete.
**Date:** 2026-11-26.

## The instruction

From the subtask title, and from the two axes P01-03.4 left open:

> Record which build is authoritative, and checksum both.

**Both** matters. There are two sequence sets for the Orvis 2022 CNS
transcriptome and they are not interchangeable, and there are two different
questions to ask about them:

1. **Which set does the project run on?** This fixes the lift-off's input,
   and with it the denominator of Gate G2 — "lifted fraction of transcriptome
   proteins" is a fraction *of something*, and the something is decided here.
2. **Which set does the project cite?** This fixes what a reader fetches when
   they want to check the work.

The two answers are not the same, and the temptation is to make them the
same because one answer is more convenient. They are recorded separately.

## The decision

| Role | File | Accession | Records | Published |
|---|---|---|---|---|
| **analysis input** | `annotation_1A-2C.fasta` (AplysiaTools) | `GJYY00000000` | **39,486** | the paper's final combined unigene count |
| **cited deposition** | `tsa.GJYY.1.fsa_nt.gz` (GenBank TSA) | `GJYY00000000` | **68,308** | the paper's "unigenes", and `stats.tsa.GJYY` |
| **excluded** | `new_unigenes.fasta` (AplysiaTools) | none | **26,849** | no published count |

**The project analyses the AplysiaTools CNS set and cites the GenBank
deposition.** The 2020 merged-unigene build is not used by any stage.

The record is `data/authoritative-build.tsv`, and it is generated and checked
by `scripts/authoritative_build.py`.

## Why the analysis input is the CNS set

The paper's own count is the argument. Fig. 1A's legend says:

> The combined 159,559 contigs were clustered based on ORFs with CD-HIT, and
> the longest ORF per cluster was identified as the unigene, yielding 71,104,
> which reduced to **39,486** unigenes with a minimum ORF length of 400 bp.

and Fig. 1C is BUSCO "for predicted protein sequences from the 2013 Broad
assembly, the DN-Trinity assembly, and **the final combined set of
unigenes**".

The AplysiaTools CNS set has **39,486** records. That is an exact match, to
the integer, with the set the paper's own completeness analysis was computed
on. The CNS set is that set.

The GenBank copy has **68,308** records, which is the paper's other published
number — "We refer to this set of 68,308 transcripts as 'unigenes', or 38,125
transcripts after filtering for those shorter than 400 bp". So the deposition
is the same build **one filter earlier**: 68,308 before the 400 bp ORF
filter, 39,486 after it.

**That is the whole of the relation, and it is a good one.** The two files are
not competing versions of the transcriptome. They are the same build at two
stages of its own curation, and the project's working set is the curated one.

Three further things support running on the CNS set:

- **It is the set the downstream stages need.** `annotation.1A-2C.trinotate.col1cut.json`
  sits beside it with the functional product names, Pfam hits and GO terms
  the curation stages consume. The GenBank flatfile carries no gene models at
  all.
- **The 12 disagreements are the CNS copy being *longer*.** P01-03.4 found 12
  transcripts that differ, and every one is the same transcript with 35 to 71
  extra bases at one end — a contiguous extension, never a difference in the
  middle. Where the two copies differ, the CNS copy is the fuller one.
- **1,357 of its transcripts were never deposited.** They are not in the TSA
  under any name, and none of them is a renamed copy of a deposited
  transcript (see below). Taking the TSA as the analysis input would silently
  drop 1,357 of the paper's final 39,486.

## Why the cited accession is the GenBank deposition

Because it is the accession. `GJYY00000000` carries a BioProject
(`PRJNA792581`), a BioSample (`SAMN24439638`) and an SRA run
(`SRR17649340`), and its master record names the assembly method — *Trinity
2.9.1; StringTie 2.1.1; PASA 2.4.1*. A reader can fetch it, and it is the
copy that a reviewer of Orvis et al. will have.

It is also the independent check. The TSA's own published aggregates
reproduce exactly from the file:

| `stats.tsa.GJYY` says | the file has |
|---|---|
| 68,308 sequences | 68,308 |
| 124,437,778 basepairs | 124,437,778 |
| NT-Largest 42,564 | 42,564 |
| NT-Smallest 303 | 303 |

So the deposition is cited *and* used as the check on the analysis input's
sequences.

## The 2020 build is excluded

`new_unigenes.fasta` is 26,849 records, dated 2020-11-11 — two years before
the Orvis 2022 assembly was deposited. It matches **no count the paper
publishes**, it shares only 8,089 identifiers with the analysis input and
12,551 with the deposition, and its `asmbl_` numeric range overlaps both.

It is a selection from the same assembly, taken earlier, and it is not the
build this project analyses. It was named in §2.1 and §3.2 only because the
pre-registration was written before the counts were compared. That is
deviation **D006**, issue **#33**.

## The two sets are the same build

This is what P01-03.4 established, and it is the foundation of the decision
above: the two files are not two assemblies, they are one assembly at two
stages.

| | |
|---|---|
| identifiers in both | **38,129** |
| identical, character for character | **38,117** |
| differ | 12 |
| in the CNS set only | **1,357** |
| in the deposition only | 30,179 |

The 12 that differ are the same transcript with extra sequence at one end.
Over the whole comparison there is not one difference in the middle of a
sequence.

## The four transcripts, stated rather than smoothed away

The paper's counts partition the 39,486 into 38,125 (from the 68,308 set)
and 1,361 (the rest). Our partition of the same 39,486 identifiers, by the
namespace they are deposited under, is 38,129 and 1,357.

**The totals agree exactly. The partition differs by four transcripts.**

Three candidate explanations were tested, and all three are ruled out:

| Hypothesis | Test | Result |
|---|---|---|
| four transcripts were renamed between the two builds | SHA-256 of every sequence in both files, matched across namespaces | **0** of the 1,357 are in the deposition under another name |
| the CNS set contains duplicate records | SHA-256 of all 39,486 sequences | 39,486 records, **39,486** distinct sequences |
| the sets differ in membership | record counts against the paper's published counts | **39,486 = 39,486** and **68,308 = 68,308**, exactly |

So the membership is identical and the naming is identical, and the residual
is in how four transcripts are attributed to an assembly arm by the paper's
custom unigene caller. **This is measured and not explained.** Resolving it
needs SI Table S3, the per-transcript list, which is behind the publisher's
supplementary file and could not be fetched.

The residual does not move the decision. It is four transcripts in 39,486 —
0.010% — and the decision rests on the exact count matches and on the
byte-level agreement of the 38,129 that overlap.

## The record

`data/authoritative-build.tsv`, one row per build:

| Role | File | Records | SHA-256 | Last modified |
|---|---|---|---|---|
| analysis-input | `annotation_1A-2C.fasta` | 39,486 | `a35b3cbc1f4e361c5a4e83227c135fa5cd792bdbe52ffa72953eb168c5b9dc6a` | 2021-04-28 |
| citable-deposition | `tsa.GJYY.1.fsa_nt.gz` | 68,308 | `a1d6bd89baf1c2212a754a93ce3cb8eef927c988c05384d7fce68445d084a892` | 2022-06-10 |
| excluded | `new_unigenes.fasta` | 26,849 | `f12aab4374de954f255d9ba4e1d8aa2bc733b56c30790a3828fd55dff8a7c3bb` | 2020-11-11 |

The two dates from AplysiaTools are the publisher's own `Last-Modified`
headers, read from the server. The deposition's date is the LOCUS line of
its master record — `10-JUN-2022` — which is the date the accession means.

**Both** are checksummed, and so is the excluded one, because a file that is
excluded today and used tomorrow should be caught by a checksum rather than
by a reader's memory.

## How to check it

```bash
python3 scripts/authoritative_build.py write   # re-derive the record from the bytes
python3 scripts/authoritative_build.py check   # verify the committed record
```

`check` verifies the structure, the roles, the agreement with
`data/manifest.tsv`, and — **wherever the raw files are present** — the
SHA-256 digests and the record counts against the files themselves. It needs
no network, and it is run in continuous integration, where the raw files are
absent because they are gitignored and re-fetchable. A check that needs the
network is a check that nobody runs.

The decision itself is **declared in the script** and derived nowhere. The
roles, the accessions and the relations are the choice; the counts, the
digests and the dates are re-derived from the files every time `write` runs.
A decision re-derived from the data it is about is not a decision, it is a
summary, and it would change under the analyst.

The tests are `tests/test_authoritative_build.py`.

## What is deliberately not done here

**The 400 bp ORF filter is not re-derived.** The claim that the CNS set is
the paper's filtered set rests on the exact count match and on the paper's
own wording. Re-deriving the filter needs a protein set, and there is none
to be had: AplysiaTools publishes no protein sequences at all (deviation
**D005**, issue **#32**). P01-10.1 derives one locally with
`aplotransDecoder` 5.7.0, and **that** is where the check belongs — the
derived protein set must reproduce the paper's 39,486 under the 400 bp ORF
filter. It is scheduled there and it is not done here.

**The pre-registration is not edited.** §2.1's row still names the
transcriptome in a way that does not choose between the two files, and §3.2
step 1 still says "the merged-unigene FASTA". Those are deviations **D004**
(issue #30), **D005** (issue #32) and **D006** (issue #33), and all three
wait for the researcher's decision.

## Note on the manifest

`data/manifest.tsv` was corrected in this subtask, because the earlier rows
carried five wrong purpose strings and put the 2020 build and the
multi-tissue annotation under the TSA accession, which they do not belong
to. The checksums did not move; the descriptions and the accession columns
did.
