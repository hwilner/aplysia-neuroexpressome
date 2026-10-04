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
