# Pre-registration deviations

Each entry is filed here *and* raised as a `deviation-log` issue, and each is
stated in the manuscript methods. The pre-registration is not edited silently.

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
