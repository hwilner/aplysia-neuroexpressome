# Pre-registration deviations

Each entry is filed here *and* raised as a `deviation-log` issue, and each is
stated in the manuscript methods. The pre-registration is not edited silently.

| Entry | Issue | Covers |
|---|---|---|
| D001 | this repository | clusterProfiler dropped; limma and edgeR taken from one Bioconductor generation |
| D002 | [#27](https://github.com/hwilner/aplysia-neuroexpressome/issues/27) | §2.2 as a whole: the base image, the InterProScan data release, MAFFT and trimAl, and the four-environment split |
| D003 | [#28](https://github.com/hwilner/aplysia-neuroexpressome/issues/28) | §2.1 names the genome assembly as `GCF_000002075.2`, an accession that does not resolve |
| D004 | [#30](https://github.com/hwilner/aplysia-neuroexpressome/issues/30) | §3.2 step 1 asks that two transcriptome sources be confirmed as the same underlying build; they are two different builds |
| D005 | [#32](https://github.com/hwilner/aplysia-neuroexpressome/issues/32) | §3.2 step 1 asks for a protein set from AplysiaTools, which publishes no protein sequences at all |
| D006 | [#33](https://github.com/hwilner/aplysia-neuroexpressome/issues/33) | §2.1's transcriptome row and §3.2 step 1 name a single lift-off source; the project runs on the AplysiaTools CNS set and cites the GenBank deposition, and the 2020 merged-unigene build is excluded |

**D002, D003, D004, D005 and D006 are open.** `materials-and-methods.md` §2.2
still describes the pre-registered toolchain, §2.1 still names an assembly
accession that cannot be fetched, §3.2 step 1 still asks for a confirmation
that cannot succeed and for a protein set that is not published, and neither
§2.1 nor §3.2 step 1 yet says which of the two transcriptome files is the
lift-off source. None of them is edited until the issue is decided.

## D001 - clusterProfiler dropped; enrichment is implemented in base R

**Date:** 2026-10-04. **Subtask:** P01-01.2. **Affects:** `materials-and-methods.md` §2.2.

**Pre-registered:** `bioconductor-clusterprofiler 4.10` in the R environment,
used for GO and KEGG over-representation (tests T6).

**Changed:** the package is removed from the image. limma is pinned at
`3.62.0` and edgeR at `4.4.0`, rather than the pre-registered `limma 3.60` and
`edgeR 4.0`.

**Why:** the solver found that `clusterProfiler 4.10` requires
`hdo.db 0.99.1`, which requires `r-base >=4.3,<4.4`. The pre-registered R is
4.4, so the two cannot coexist. clusterProfiler is the only thing in the
project that makes R 4.4 unsolvable, and the analysis it was named for is a
hypergeometric test per term with Benjamini-Hochberg FDR across terms. That is
implemented directly in base R against a GO/KEGG gene-to-term map.

**Consequence:** no change to the statistical procedure, the assumptions, the
background, or the multiple-testing policy stated in the pre-registration. The
change is to which library computes it, and it must be stated in the methods.

**Also corrected, and this took three solver rounds to get right.** The
pre-registration named `limma 3.60`, which does not exist on any channel. The
Bioconductor packages must be taken from one generation:

| Generation | R | limma | edgeR |
|---|---|---|---|
| 3.18 | 4.3 | 3.58.x | 4.0 |
| 3.20 | 4.4 | 3.62.x | 4.4.x |

Taking `edgeR 4.0` forces limma 3.58.1, which forces R 4.3 and contradicts the
pre-registered R 4.4. The 3.20 pair — `limma 3.62.0` with `edgeR 4.4.0` — keeps
R 4.4 as pre-registered. **R 4.4 is therefore unchanged; only the two
Bioconductor pins move.**

Worth recording: the whole R stack is a three-round detour caused by pinning
`limma 3.60`, a version that never existed, and by treating edgeR 4.0 as
independent of it.

**Reversal:** revert the pin and reinstall clusterProfiler, and run the R stack
on R 4.3 instead. Do not do this without a solver check first.

## D002 - the software environment in §2.2 is described as one environment, and the image is not

**Date:** 2026-10-29. **Subtask:** P01-01.2. **Affects:** `materials-and-methods.md` §2.2.

**Pre-registered:** §2.2 describes a `mambaforge` 23.11 base and a single
environment, with InterProScan 5.70-102.0, `metafor` 4.4, `tidyverse`,
`rstatix` and `lme4` among the statistics tools, and a Jupyter 1.x
interpreter stage for notebooks and figure provenance.

**Changed:** the image is four environments, built with micromamba 2.9.0, with
InterProScan 5.59-91.0. The statistics environment now also carries `lme4`
and `tidyverse`, which the pre-registration names and the image did not have.
`metafor` is pinned at 4.6_0 rather than 4.4, because no build of 4.4
accepts R 4.4. Liftoff and OrthoFinder come from bioconda rather than from
git checkouts. There is no Jupyter stage.

**Why:** each of these was forced by the solver or by the package index, and
none of them changes the analysis.

| §2.2 says | The image has | Why |
|---|---|---|
| `mambaforge` 23.11 | micromamba 2.9.0 | `mambaforge` 23.11 does not exist; micromamba 2.9.0 is the published base image |
| one environment | four: `bio`, `tree`, `r`, `ips` | a single solve spanning bioconda, conda-forge's R stack and InterProScan's own library tree is fragile by construction, and a conflict in one of them then rules out all the others |
| `InterProScan` 5.70-102.0 | 5.59-91.0 | bioconda's newest InterProScan build is 5.59-91.0; 5.70-102.0 is not distributed on conda |
| `metafor` 4.4 | 4.6_0 | `metafor` 4.4_0 has no build for R 4.4; 4.6_0 does |
| `lme4`, `tidyverse` | present | they were named in §2.2 and missing from the image |
| Jupyter 1.x | absent | there is no analysis code, and so no notebook and no figure provenance to produce yet |
| Liftoff from commit `b8a41b0` | `liftoff 1.3.0` from bioconda | the base image carries no `git`, so the checkout could not have been installed; the bioconda package is the upstream 1.3.0 release and declares its dependencies |

**Consequence:** no change to the statistical procedure, the assumptions, the
background, or the multiple-testing policy stated in the pre-registration. The
R version is still 4.4, the Bioconductor pair is still the 3.20 generation, and
every pre-specified test is still run by the tool the pre-registration names.
The InterProScan data release does change, and for that reason the methods
must state 5.59-91.0 and the catalogue must record the InterProScan version
beside every domain hit; that was already flagged in
`docs/P01-01-2-image-build.md` as a subtask still to be raised.

**Reversal:** the environment split can be undone by moving the pins back into
one `micromamba create`, but only after a solver check confirms the single
transaction still resolves. The InterProScan data release can be restored by
installing 5.70-102.0 from the InterProScan distribution instead of conda, at
the cost of Java 11 and a much longer build.

## D003 - the assembly accession in §2.1 does not resolve

**Date:** 2026-11-10. **Subtask:** P01-02.2. **Affects:** `materials-and-methods.md` §2.1.

**Pre-registered:** the genome assembly as `GCF_000002075.2` (AplCal3.0),
assembly release 2013.

**Changed:** the assembly is fetched from `GCF_000002075.1`, the RefSeq
accession for AplCal3.0, as `GCF_000002075.1_AplCal3.0_genomic.fna.gz`. The
GenBank twin is `GCA_000002075.2`.

**Why:** `GCF_000002075.2` does not exist. It is the RefSeq prefix paired
with the GenBank version number. Four independent sources give the RefSeq
accession as `GCF_000002075.1`: the assembly report inside the download
itself, NCBI's Release 102 annotation readme, the assembly record in NCBI's
database, and the file path, where the `.2` directory returns HTTP 404.

The assembly itself was never in doubt. AplCal3.0 is one assembly, submitted
by the Broad Institute on 2013-05-15, and its RefSeq and GenBank copies
carry identical statistics: 4,331 scaffolds, scaffold N50 917,541, 927,310,431
bases with the mitochondrion included. The downloaded file was checked
against NCBI's published MD5, checked with `gzip -t`, and read to confirm
that every sequence header carries `AplCal3.0`.

**Consequence:** none for the analysis. The same assembly is used, and the
correct identifier is the only thing that changed. No result has been seen,
because no analysis has been run. The methods must state the accession that
was actually used, and the decision on what §2.1 should say is issue #28's.

**The same string is in two other pre-registrations.** Checked rather than
assumed:

| repository | line | as written |
|---|---|---|
| `aplysia-buccatlas` | `materials-and-methods.md` §2.1 | `GCF_000002075.2` + Release 102 |
| `aplysia-agechannels` | `materials-and-methods.md` §2.1 | `GCF_000002075.2` + RefSeq Release 102 |

`aplysia-tempq10` does not name the assembly and is unaffected. All three
say the same thing and all three are wrong in the same way. None of them has
been edited: one decision in issue #28 can settle all three.

**Reversal:** nothing to reverse. The same sequence content is available
under the GenBank accession, so citing that instead is a one-line change to
the fetch script and a re-verification of the checksums.

## D004 - the two transcriptome sources are two different builds

**Date:** 2026-11-22. **Subtask:** P01-03.3. **Affects:** `materials-and-methods.md` §3.2 step 1.

**Pre-registered:** "Obtain the merged-unigene FASTA and predicted protein set
from AplysiaTools; obtain the Orvis 2022 assembly from GenBank. Confirm the
two are the same underlying build by comparing sequence counts and a random
sample of 50 sequences."

**Changed:** the counts are compared, and the comparison is reported. The
merged-unigene FASTA and the Orvis 2022 assembly are **not** confirmed to be
the same build, because they are not: they are two different builds, published
two years apart. The AplysiaTools file that does correspond to the Orvis 2022
assembly is the **predicted protein set**, `annotation_1A-2C.fasta`. P01-03.4's
50-sequence sample is run on that pair.

**Why:** the AplysiaTools directory is not one build. It holds files from four
years — `new_unigenes.fasta` 2020-11-11, `annotation_1A-2C.fasta` 2021-04-28,
the six per-tissue files 2023-02-10, `current.annotation.fasta` 2025-07-15 —
while the Orvis 2022 assembly was deposited on 2022-06-10.

| | merged unigenes | CNS protein set | TSA |
|---|---|---|---|
| records | 26,849 | 39,486 | 68,308 |
| `asmbl_` / `TRINITY_DN` | 24,099 / 2,750 | 13,314 / 26,172 | 23,003 / 45,305 |
| identifiers also in the TSA | 12,551 (46.7%) | 38,129 (96.6%) | — |
| a count the paper publishes | none | **39,486** | **68,308** |

The paper's own four counts locate the builds exactly: 68,308 is the GenBank
TSA, the full unigene set before the ORF filter; 39,486 is the AplysiaTools CNS
protein set, that set after the filter. The `asmbl_` numeric ranges are the same
in all three files (1–341,054 / 40–341,049 / 7–341,053), so these are two
selections from one assembly taken at different times rather than two unrelated
assemblies. Of the merged file's 24,099 `asmbl_` identifiers, 10,458 are in the
TSA and 13,641 are not.

**Consequence:** the pre-registered confirmation cannot be satisfied as
written, and P01-03.4 must not be run against the merged-unigene FASTA, where a
negative result would say something about the 2020 build and nothing about the
data. The pre-specified comparison is still run and still reported; it reports
a disagreement, and the note says which pair the disagreement is about. No
result has been seen, because no analysis has been run. The decision on what
§3.2 step 1 should say is issue #30's.

## D005 - AplysiaTools publishes no protein set

**Date:** 2026-11-24. **Subtask:** P01-03.4. **Affects:** `materials-and-methods.md` §3.2 step 1.

**Pre-registered:** "Obtain the merged-unigene FASTA **and predicted protein
set** from AplysiaTools; obtain the Orvis 2022 assembly from GenBank."

**Changed:** the merged-unigene FASTA and the CNS set are obtained from
AplysiaTools and the Orvis 2022 assembly from GenBank, as pre-registered. The
**protein set is derived locally** from the nucleotide, by `aplotransDecoder`
5.7.0, which §2.2 already pins and P01-10.1 already schedules. It is not
obtained from AplysiaTools, because there is nothing there to obtain.

**Why:** every transcriptome file AplysiaTools publishes is nucleotide. Over
the whole of each file, not a sample: `new_unigenes.fasta` is 100.0000% A/C/G/T
over 94,756,984 residues; `annotation_1A-2C.fasta` is 100.0000% over
93,862,417; `current.annotation.fasta` is 99.9998% over 409,016,873, the
remainder being 797 `N`. The six per-tissue files under `/unigenes/` are
nucleotide too, despite `longestorfs` in their names. The Trinotate JSON
carries no peptide, and the Trinotate report's peptide column is empty. The
site has two directories and no protein FASTA in either.

This also corrects an error of the assistant's own: the notes for P01-03.1,
P01-03.2 and P01-03.3 called `annotation_1A-2C.fasta` and
`current.annotation.fasta` protein sets. They are not, and the three notes
now carry a dated correction banner. The counts and the overlaps in them are
unaffected.

**Consequence:** none for the analysis. §3.2 step 2 and P01-10.1 already
produce the protein set locally, from the nucleotide, with a pinned tool. The
methods must state that the protein set is derived rather than downloaded.
The decision on what §3.2 step 1 should say is issue #32's.

**The 50-sequence comparison the instruction asks for was run, and it
confirms the two sources are the same build.** Over every shared transcript:
the CNS set against the TSA is 38,117 identical, 12 differing and 1,357
absent; the merged unigenes against the TSA is 12,551 identical and 0
differing; the CNS set against the merged unigenes is 8,089 identical and 0
differing. The twelve are the same transcript with 35 to 71 extra bases at one
end. Nothing was changed to make that result: the sample is seeded, the
identifiers are sorted before the draw, and the comparison is also run
exhaustively. The protein set's provenance bears on none of it.

## D006 - the lift-off source is named, and it is not the merged-unigene FASTA

**Date:** 2026-11-26. **Subtask:** P01-03.5. **Affects:** `materials-and-methods.md` §2.1's transcriptome row and §3.2 step 1.

**Pre-registered:** §2.1 names one transcriptome assembly, "GenBank TSA
`GJYY00000000` (Orvis et al. 2022); also via AplysiaTools `aplysiatools.org`",
with "Lift-off source, gene-model repair source" in the *Used for* column.
§3.2 step 1 names the merged-unigene FASTA as the thing to obtain and to
confirm.

**Changed:** the lift-off source is named, and it is **the AplysiaTools CNS
set**, `annotation_1A-2C.fasta`, 39,486 records, SHA-256
`a35b3cbc1f4e361c5a4e83227c135fa5cd792bdbe52ffa72953eb168c5b9dc6a`. The
GenBank TSA `GJYY00000000` remains the accession the project cites and the
independent check on the sequences. The merged-unigene FASTA,
`new_unigenes.fasta`, 26,849 records, is **excluded** from every stage. The
decision is recorded in `data/authoritative-build.tsv` and checked by
`scripts/authoritative_build.py`.

**Why:** the two files are the same build at two stages of its own curation,
and the paper's own counts say which stage is which.

| | the paper says | the file has |
|---|---|---|
| final combined unigenes at a 400 bp ORF filter (Fig. 1A) | **39,486** | 39,486 in `annotation_1A-2C.fasta` |
| the deposited "unigenes", before that filter | **68,308** | 68,308 in the TSA, and `stats.tsa.GJYY` agrees |
| after filtering for those shorter than 400 bp | 38,125 | 38,129 identifiers in the TSA, 1,357 not |

Fig. 1C's BUSCO is on "the final combined set of unigenes", so 39,486 is the
set the paper's own completeness analysis was computed on. Using it as the
analysis input is what makes the project's numbers comparable with the
paper's.

Three further reasons point the same way. **The strongest is that the
functional annotation's identifiers are the set's identifiers, exactly.**
AplysiaTools publishes the Trinotate annotation of the CNS set beside it,
`annotation.1A-2C.trinotate.col1cut.json`, and it has 39,486 entries whose
identifiers are the CNS set's identifiers and nothing else — not one more,
not one fewer, no identifier on either side that the other lacks. Two
independent files agree on their membership completely, and a curation step
that dropped, split or renamed a transcript would have broken that. Every
entry carries a product name and at least one Pfam hit; 22,145 carry GO
terms. The 1,357 transcripts that the CNS set has and the deposition does
not are **not** in the deposition under any name, and none of them is a
renamed copy of a deposited transcript: every sequence in both files was
hashed and the cross-namespace match count is zero. Taking the TSA as the
analysis input would silently drop 1,357 of the paper's final 39,486.
Where the two copies do differ, in 12 transcripts, the CNS copy is the
**longer** one, by a contiguous extension of 35 to 71 bases at one end. And
the CNS set is the one whose functional annotation the curation stages need,
while the GenBank flatfile carries no gene models at all.

The 2020 build is excluded because it matches no count the paper publishes,
and it was named in the pre-registration only because the pre-registration was
written before the counts were compared.

**Consequence:** none for the analysis, and none that has been seen — no
analysis has been run yet. What changes is which file the later stages read.
Gate G2's denominator follows from it: the lifted fraction is a fraction of
the 39,486-transcript analysis set, not of the 68,308-transcript deposition.
§3.2 step 1's comparison is still run and still reported, and it reports
agreement for the pair that matters.

**The one residual, stated rather than smoothed away.** The paper's counts
partition the 39,486 into 38,125 and 1,361; the namespace partitions the same
39,486 into 38,129 and 1,357. The totals agree exactly and the partition
differs by four transcripts. Renaming is ruled out (0 cross-namespace
sequence matches), duplication is ruled out (39,486 records, 39,486 distinct
sequences), and differing membership is ruled out (both published counts match
exactly). The residual is four transcripts in 39,486 — 0.010% — and it does
not move the decision. Resolving it needs SI Table S3, the per-transcript
list, which could not be fetched.

**Reversal:** the analysis input is one line in `data/authoritative-build.tsv`
and one constant in `scripts/authoritative_build.py`. Changing it means
re-running `scripts/authoritative_build.py write`, and the record counts and
digests would be re-derived from the new file rather than typed.

