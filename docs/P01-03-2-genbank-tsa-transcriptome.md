# P01-03.2 — the Orvis 2022 transcriptome from GenBank

**Subtask:** P01-03.2 — download the Orvis 2022 assembly from GenBank TSA `GJYY00000000`.
**Status:** complete.
**Date:** 2026-11-20.

## What was fetched

Four files from `https://ftp.ncbi.nlm.nih.gov/genbank/tsa/G/`.

| File | Bytes | What it is |
|---|---|---|
| `tsa.GJYY.1.fsa_nt.gz` | 36,965,264 | the transcriptome sequences, in FASTA |
| `tsa.GJYY.1.gbff.gz` | 56,761,667 | the same sequences in GenBank flatfile format |
| `tsa.GJYY.mstr.gbff.gz` | 1,383 | the master record: the deposition's own metadata |
| `stats.tsa.GJYY` | 96 | the publisher's own counts for the project |

All four are last written **11 June 2022**. SHA-256 for each is in
`data/manifest.tsv`; the raw files stay uncommitted and are re-fetched by
`scripts/fetch_transcriptomes.sh`.

The route matters. The nuccore page for `GJYY00000000` is behind a
reCAPTCHA, and the NCBI datasets API has no route for a TSA master. The FTP
has both, and no captcha:

```
https://ftp.ncbi.nlm.nih.gov/genbank/tsa/G/tsa.GJYY.1.fsa_nt.gz
```

## The verification is better than a checksum

The publisher publishes no checksum for these files. But `stats.tsa.GJYY` is
96 bytes and publishes four aggregates the publisher computed from its own
copy:

```
NCBI_TSA_master|GJYY|01|NT-Sequences|68308|Basepairs|124437778|NT-Largest|42564|NT-Smallest|303
```

The downloaded file reproduces **all four exactly**:

| | Publisher | The file |
|---|---|---|
| sequences | 68,308 | 68,308 |
| basepairs | 124,437,778 | 124,437,778 |
| longest | 42,564 | 42,564 |
| shortest | 303 | 303 |

`scripts/fetch_transcriptomes.sh` recomputes these on every run and refuses
to continue on a mismatch. That is a stronger check than a checksum of a file
we already have: four independent numbers the publisher computed separately.
It was checked in both directions — the real file matches, and a deliberately
wrong file is caught.

## What the master record says

Twenty-five strings are captured verbatim into `data/versions.tsv`, extracted
from the record rather than retyped. The ones that pin the version:

| | |
|---|---|
| Project accession | `GJYY00000000` |
| Version | `GJYY00000000.1` |
| This version's accession | `GJYY01000000` |
| Its sequences | `GJYY01000001-GJYY01068308` |
| LOCUS date | `10-JUN-2022` |
| BioProject | `PRJNA792581` |
| BioSample | `SAMN24439638` |
| SRA | `SRR17649340` |
| Assembly name | `Aplysia_CNS` |
| Assembly method | `Trinity 2.9.1; StringTie 2.1.1; PASA 2.4.1` |
| Sequencing technology | `Illumina HiSeq` |
| Submitted | `15-MAY-2022` |
| Reads | `2.97 billion Illumina HiSeq reads` |
| `/tissue_type` | `CNS` |
| `/db_xref` | `taxon:6500` |
| `/sex` | `hermaphrodite` |

**`10-JUN-2022` is the pre-registration's "Deposited 2022-06-10"** — the
version pin in §2.1, confirmed by the deposition itself. And `/tissue_type` is
`CNS`, so this really is the CNS transcriptome and not the whole animal.

## The count is the paper's count

68,308 is exactly the number in Orvis et al. 2022:

> We refer to this set of 68,308 transcripts as "unigenes," or 38,125
> transcripts after filtering for those shorter than 400 bp.

So the GenBank copy is the paper's **full unigene set**, before the filter.
The paper's other arm — 71,104 CD-HIT clusters reduced to 39,486 at a minimum
400 bp ORF — is the filtered set, and **39,486 is exactly the AplysiaTools
protein set's size** (P01-03.1). The two copies are the same study at two
stages of its own pipeline.

## The identifier bridge

This is the part that makes the comparison possible at all.

The TSA numbers its sequences `GJYY01000001` to `GJYY01068308`. AplysiaTools
calls them `asmbl_N` or `TRINITY_DN...`. **The two namespaces are disjoint**,
and the FASTA carries nothing that relates them.

The flatfile does. Every TSA record's DEFINITION line carries the name the
sequence had in the original assembly:

```
DEFINITION  TSA: Aplysia californica isolate field caught, aquaculture reared
              TRINITY_DN69521_c0_g1_i1, transcribed RNA sequence.
```

`scripts/extract_tsa_names.py` reads all 68,308 of them out and writes
`data/derived/tsa_transcript_names.tsv`: **45,305 `TRINITY_DN` names and
23,003 `asmbl_` names.** Without this the two copies could only be compared
by sequence content; with it they can be compared by name.

## Which copy contains which — and it is not the one P01-03.1 guessed

Using that mapping:

| AplysiaTools file | Its identifiers also in the TSA |
|---|---|
| predicted protein set (39,486) | **38,129** — 96.5% |
| `new_unigenes.fasta` (26,849) | **12,551** — 46.7% |

And within the protein set, **all 13,314 of its `asmbl_` identifiers are in
the TSA**, together with 24,815 of its 26,172 `TRINITY_DN` ones.

So the ordering is:

- the **protein set** is essentially the TSA's content, filtered down to the
  paper's 39,486;
- the **nucleotide file** is the outlier — barely half of it is in the TSA at
  all.

P01-03.1 compared AplysiaTools' nucleotide file against AplysiaTools' protein
set and found only 8,089 shared identifiers, and recorded that the two were
"not the same sequence set". That is true and it stands, but the third copy
now shows which of the two is the strange one: it is the nucleotide file. The
addendum to `P01-03-1-aplysiatools-transcriptome.md` says so.

## Two things the file does not contain

**The TSA carries no gene models.** The flatfile has 68,308 `source` features
and nothing else — no `exon`, no `CDS`. It is a sequence-only deposition. Any
transcriptome gene model has to come from elsewhere: AplysiaTools'
Trinotate annotation, or a fresh ORF prediction.

**The paper's 400 bp filter is on ORFs, not on transcripts.** The paper says
*"reduced to 39,486 unigenes with a minimum ORF length of 400 bp"* — the
length of the coding region, not of the sequence. Filtering the TSA by
sequence length gives a different number: **60,173** of its 68,308 sequences
are at least 400 nt, and 8,135 are shorter. So the 39,486 cannot be
reproduced from the sequence lengths, and it cannot be checked without the
ORF calls. That is a real limitation on what P01-03.3 can verify from the
sequence file alone, and it is worth knowing before the comparison is
attempted.

## The length distributions

| | TSA | `new_unigenes.fasta` |
|---|---|---|
| sequences | 68,308 | 26,849 |
| total bases | 124,437,778 | 94,756,984 |
| shortest | 303 | 297 |
| longest | 42,564 | 48,455 |
| median | 995 | 2,366 |

Both extremes differ, and the median differs by more than a factor of two.
The TSA has more sequences and more bases but a much shorter median, which is
what an unfiltered set that contains many short transcripts looks like.

## What was not fetched, and why

Nothing else from the TSA project. The `tsa.GJYY.1.gbff.gz` flatfile was
initially left alone on the grounds that the pre-registration names the
FASTA — and it was fetched anyway, because it turned out to carry the
identifier mapping, which is the only thing that makes the two copies
comparable by name. That was the right call, and it was not obvious from the
file name.

## How to check

```bash
scripts/fetch_transcriptomes.sh      # re-verifies all eight files, and the TSA aggregates
python3 scripts/extract_tsa_names.py  # rebuilds the accession-to-name mapping
python3 -m unittest discover -s tests
```

## Note on the manifest

The `md5_source` column reads `none published` for these rows, because no
MD5 is published for them. That is not the whole of the verification, and the
`purpose` column says so for the FASTA: its record count, base total and
length extremes all match the publisher's published aggregates in
`stats.tsa.GJYY`.
