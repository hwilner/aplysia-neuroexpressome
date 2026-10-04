# Pre-registration deviations

Each entry is filed here *and* raised as a `deviation-log` issue, and each is
stated in the manuscript methods. The pre-registration is not edited silently.

## D001 - clusterProfiler dropped; enrichment is implemented in base R

**Date:** 2026-10-04. **Subtask:** P01-01.2. **Affects:** `materials-and-methods.md` §2.2.

**Pre-registered:** `bioconductor-clusterprofiler 4.10` in the R environment,
used for GO and KEGG over-representation (tests T6).

**Changed:** the package is removed from the image. limma is pinned at
`3.58.1` rather than the pre-registered `3.60`.

**Why:** the solver found that `clusterProfiler 4.10` requires
`hdo.db 0.99.1`, which requires `r-base >=4.3,<4.4`. The pre-registered R is
4.4, so the two cannot coexist. clusterProfiler is the only thing in the
project that makes R 4.4 unsolvable, and the analysis it was named for is a
hypergeometric test per term with Benjamini-Hochberg FDR across terms. That is
implemented directly in base R against a GO/KEGG gene-to-term map.

**Consequence:** no change to the statistical procedure, the assumptions, the
background, or the multiple-testing policy stated in the pre-registration. The
change is to which library computes it, and it must be stated in the methods.

**Also corrected:** the pre-registration named `limma 3.60`, which does not
exist on any channel. edgeR 4.0 requires `limma >=3.58.0,<3.59.0`, so
`3.58.1` is the only release that satisfies it.

**Reversal:** revert the pin and reinstall clusterProfiler, and run the R stack
on R 4.3 instead. Do not do this without a solver check first.
