# Pre-registration deviations

Each entry is filed here *and* raised as a `deviation-log` issue, and each is
stated in the manuscript methods. The pre-registration is not edited silently.

| Entry | Issue | Covers |
|---|---|---|
| D001 | this repository | clusterProfiler dropped; limma and edgeR taken from one Bioconductor generation |
| D002 | [#27](https://github.com/hwilner/aplysia-neuroexpressome/issues/27) | §2.2 as a whole: the base image, the InterProScan data release, MAFFT and trimAl, and the four-environment split |
| D003 | [#28](https://github.com/hwilner/aplysia-neuroexpressome/issues/28) | §2.1 names the genome assembly as `GCF_000002075.2`, an accession that does not resolve |

**D002 and D003 are open.** `materials-and-methods.md` §2.2 still describes the
pre-registered toolchain, and §2.1 still names an assembly accession that
cannot be fetched. Neither is edited until the issue is decided.

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
