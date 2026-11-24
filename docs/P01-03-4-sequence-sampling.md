# P01-03.4 — fifty sequences, compared

**Subtask:** P01-03.4 — extract 50 random sequences and confirm they are identical.
**Status:** complete.
**Date:** 2026-11-24.

## The instruction

§3.2, step 1 of `materials-and-methods.md`:

> Obtain the merged-unigene FASTA and predicted protein set from AplysiaTools;
> obtain the Orvis 2022 assembly from GenBank. Confirm the two are the same
> underlying build by comparing sequence counts and a random sample of 50
> sequences.

P01-03.3 compared the counts and found the two sources do not agree, and
why. This note does the sampling half, and it does the counts' complement:
**every transcript the two sources have in common, compared character for
character.**

## First, a correction that changes what "identical" means

**All three AplysiaTools transcriptome files are nucleotide. There is no
protein FASTA at AplysiaTools.**

This was checked over the whole of each file, not a sample:

| File | Records | Residues | A/C/G/T fraction | Letters other than A, C, G, T |
|---|---|---|---|---|
| `new_unigenes.fasta` | 26,849 | 94,756,984 | 1.000000 | none |
| `annotation_1A-2C.fasta` | 39,486 | 93,862,417 | 1.000000 | none |
| `current.annotation.fasta` | 196,953 | 409,016,873 | 0.999998 | 797 `N` |

Not one amino-acid letter in half a gigabase. The per-tissue files under
`/unigenes/` are nucleotide too, despite `longestorfs` in their names, and
the Trinotate JSON carries no peptide — only an identifier, a product name,
Pfam hits and GO terms. The `merged.unigenes.trinotate.xls` report has 16
columns and the peptide column is empty for the rows checked.

So "confirm they are identical" is a **byte-for-byte comparison of
nucleotide sequences**, which is the sharpest form the test can take. The
earlier notes' term "protein set" for two of these files was wrong, and the
three notes that used it now carry a correction banner. The counts and the
overlaps in them are unaffected.

**A second correction.** P01-03.2 said the GenBank flatfile was the only
record of the mapping between the two identifier namespaces. It is not. The
TSA **FASTA's own headers carry the original assembly name**:

```
>GJYY01000001.1 TSA: Aplysia californica isolate field caught, aquaculture reared TRINITY_DN69521_c0_g1_i1, transcribed RNA sequence
```

All 68,308 headers do, and every one agrees with the flatfile's mapping.
The flatfile is the second, independent record, not the only one.
`scripts/sample_transcriptome_sequences.py` reads the headers and checks
them against the flatfile, and refuses to run if they disagree.

## The sample

Seed **20261005** — the programme-wide seed, the same value the statistical
tests use. The identifiers are sorted before the draw, so the sample does
not depend on the order the file happens to be in. Size 50 per comparison.

**A — the merged unigenes against the TSA.** This is the comparison §3.2
step 1 names.

| | |
|---|---|
| identical | **20** of 50 |
| differ | **0** |
| not in the TSA | 30 |

Every merged-unigene sequence that the TSA also carries is identical to it.
Not one differs.

**B — the CNS set against the TSA.** This is the pair the lift-off depends
on.

| | |
|---|---|
| identical | **50** of 50 |
| differ | 0 |
| not in the TSA | 0 |

**C — the CNS set against the merged unigenes.** The two files have only
8,089 transcripts in common, so the draw is from the intersection rather
than from either file.

| | |
|---|---|
| identical | **50** of 50 |
| differ | 0 |
| — | — |

## The same comparison over every shared transcript

The sample answers the pre-registered question. The same comparison over
every shared transcript costs nothing, because the sequences are already in
hand, and it turns "50 of 50 agreed" into a statement about the whole set.

| Comparison | Identical | Differ | Not in the other | Compared |
|---|---|---|---|---|
| CNS set against the TSA | **38,117** | **12** | 1,357 | 39,486 |
| merged unigenes against the TSA | **12,551** | **0** | 14,298 | 26,849 |
| CNS set against the merged unigenes | **8,089** | **0** | 31,397 | 39,486 |

**There is not one differing sequence in 20,640 shared transcripts between
the merged unigenes and the CNS set, and not one in the 12,551 the merged
unigenes share with the TSA.** The only disagreements anywhere are 12
transcripts, all of them between the CNS set and the TSA.

## The twelve

All twelve are the same transcript with extra sequence at one end — a
slightly longer copy in the AplysiaTools file. Never a difference in the
middle.

| Transcript | Difference | What it is |
|---|---|---|
| `TRINITY_DN112932_c0_g1_i2` | +35 nt | the CNS copy has 35 nt more at the 5′ end |
| `TRINITY_DN100754_c0_g2_i1` | +35 nt | the CNS copy has 35 nt more at the 5′ end |
| `TRINITY_DN28874_c0_g1_i1` | +46 nt | the CNS copy has 46 nt more at the 5′ end |
| `TRINITY_DN21759_c0_g1_i1` | +46 nt | the CNS copy has 46 nt more at the 3′ end |
| `TRINITY_DN31038_c0_g1_i9` | +53 nt | the CNS copy has 53 nt more at the 5′ end |
| `TRINITY_DN102387_c0_g2_i1` | +54 nt | the CNS copy has 54 nt more at the 3′ end |
| `TRINITY_DN153_c4_g1_i2` | +55 nt | the CNS copy has 55 nt more at the 5′ end |
| `TRINITY_DN279799_c0_g1_i1` | +55 nt | the CNS copy has 55 nt more at the 3′ end |
| `TRINITY_DN11733_c0_g1_i3` | +56 nt | the CNS copy has 56 nt more at the 3′ end |
| `TRINITY_DN79354_c0_g1_i1` | +59 nt | the CNS copy has 59 nt more at the 5′ end |
| `TRINITY_DN252891_c0_g1_i1` | +64 nt | the CNS copy has 64 nt more at the 5′ end |
| `TRINITY_DN21344_c1_g1_i6` | +71 nt | the CNS copy has 71 nt more at the 3′ end |

Seven at the 5′ end and five at the 3′ end, between 35 and 71 nt. In every
case the TSA's copy is a contiguous sub-sequence of the AplysiaTools copy,
so these are the same transcript assembled with a slightly longer end.

## What it means

**The two sources agree exactly wherever they overlap.** The difference
between them is not in the sequences but in which transcripts they carry —
and P01-03.3 already measured that: the CNS set has 39,486 transcripts, the
TSA has 68,308, and they share 38,129 by name. The other 1,357 of the CNS
set's transcripts are not in the TSA under those names.

This refines P01-03.3's finding rather than reversing it. The merged-unigene
FASTA and the Orvis 2022 assembly are still two different *selections*, from
different years, out of the same assembly — but where they overlap they are
the same sequences, character for character, with no exceptions at all in
20,640 shared transcripts.

**So the pre-registered confirmation does succeed — for the pair that
matters.** The CNS set and the Orvis 2022 TSA are the same build. The
merged-unigene FASTA is a different, earlier selection of the same
assembly, and it agrees with the CNS set wherever both are present.

**The lift-off's source is settled in practice:** the TSA and the CNS set
describe the same transcripts, so the transcriptome the project lifts is the
Orvis 2022 CNS transcriptome either way. P01-03.5 records which build is
authoritative.

## One thing the pre-registration asks for that does not exist

§3.2 step 1 says to obtain "the merged-unigene FASTA **and predicted protein
set** from AplysiaTools". There is no protein set there to obtain — see the
alphabet table above. The merged-unigene FASTA and the CNS set are both
nucleotide, the Trinotate JSON carries no peptide, and the site publishes no
protein FASTA in any directory.

The protein set therefore has to be **derived locally**, which is what
P01-10.1 ("Run aplotransDecoder on the transcriptome") and §2.2's `decode`
pin already provide for, and §3.2 step 2 assumes. The pre-registration's
analysis is unaffected; only the provenance of one input is misdescribed.
This is filed as deviation **D005**, issue **#32**, and the pre-registration
is not edited.

## How to check

```bash
python3 scripts/fetch_transcriptomes.sh       # the eight files, checksums re-verified
python3 scripts/extract_tsa_names.py           # the accession -> original-name mapping
python3 scripts/sample_transcriptome_sequences.py
```

The last one writes four derived files:

| File | What it holds |
|---|---|
| `data/derived/sequence_sample.tsv` | one row per sampled item, with its verdict |
| `data/derived/sequence_sample_merged.fasta` | the 50 sampled merged-unigene sequences |
| `data/derived/sequence_sample_cns.fasta` | the 50 sampled CNS sequences |
| `data/derived/sequence_exhaustive.tsv` | the counts over every shared transcript |
| `data/derived/sequence_differences.tsv` | the twelve that differ, and how |

The derived files are not committed; the script that makes them is. The
tests are `tests/test_sequence_sampling.py`.

## Note on the manifest

Nothing was added to `data/manifest.tsv`: this subtask read files that
P01-03.1 and P01-03.2 had already fetched and recorded, and added no new
input.
