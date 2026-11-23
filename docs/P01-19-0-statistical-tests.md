# P01-19.0 · the pre-registered statistical tests, implemented before the data

**Date:** 2026-11-23. **Subtask:** P01-19 (infrastructure, ahead of the
registered window). **Affects:** nothing measured; this note records an
implementation, not a result.

## What was built

`scripts/prereg_stats.py` implements, in the Python standard library only,
the tests pre-registered in `materials-and-methods.md` §5.2 for P01-19:

- **T1** — McNemar's test on the paired BUSCO ortholog outcomes, with the
  pre-registered decision rule wired in: fewer than 10 discordant pairs
  skips the test and reports only the difference in proportion with its
  interval; fewer than 25 uses the exact binomial form; otherwise the
  chi-square form with continuity correction. The interval is Newcombe's
  method 10, the Wilson-based interval for a *paired* difference of
  proportions — the paired form of what §5.2's T1 row asks for.
- **T2 / T3** — Wilcoxon signed-rank on paired CDS lengths and exon
  counts: exact p by subset-sum enumeration over the (possibly tied)
  midranks when n ≤ 25, tie-corrected normal approximation with
  continuity correction above it; effect size is the matched-pairs
  rank-biserial correlation. The pre-registered assumption check (more
  than 20% of differences must be non-zero) routes to a seeded sign-flip
  permutation test on the mean difference when it fails, and the
  pre-registered fallback interval — bootstrap BCa on the median
  difference — is implemented alongside.
- **T4** — the cross-annotation BUSCO comparison: chi-square on the 3×2
  table when every expected count is ≥ 5, Fisher–Freeman–Halton exact
  otherwise, pairwise Fisher post-hocs with Holm adjustment in either
  case, and — when the exact enumeration exceeds a declared cap — an
  explicit degradation to the pre-registered fallback (proportions with
  Wilson intervals, reported as descriptive), which raises rather than
  approximating.
- **T10** — Welch's t-test with Welch–Satterthwaite degrees of freedom
  (the pooled-variance variant is deliberately not offered, per §5.2),
  Hedges' g as the effect size, and Mann–Whitney U as the fallback.

## Design decisions, fixed before any data are seen

- **One seed, declared once.** Every resampling procedure defaults to
  `P01_DEFAULT_SEED = 20261005` (the P01 kickoff date), so a re-run is
  byte-identical.
- **The exact Wilcoxon is exact for ties.** The subset-sum enumeration
  runs over the midranked values, not over the integers 1…n, so tied
  absolute differences get the correct conditional distribution. On
  distinct ranks it reproduces the standard reference implementation's
  exact mode to machine precision; on a tied fixture the two disagree
  (0.7006 vs 0.7148) and the subset-sum value is the one brute-force
  enumeration of all sign assignments produces — the test file keeps
  both numbers so nobody "fixes" the implementation to match the
  distinct-rank formula.
- **Two-sided Fisher sums probability-ordered tables** (R's
  `fisher.test` definition), in the log domain, so BUSCO-scale counts do
  not overflow.
- **The Newcombe method-10 interval reduces to the independent
  square-and-add form when the paired phi coefficient is zero** and
  narrows under positive correlation; both properties are pinned by
  tests.

## Validation

`tests/test_prereg_stats.py`, 41 tests. Reference values are fixed before
any analysis data exist: the small cases are computed by hand or by exact
enumeration inside the test file (the tea-tasting table, a 6-pair
sign-flip enumeration, the 26-table Fisher–Freeman–Halton enumeration),
and the larger ones were cross-checked once against an independent,
widely-audited statistics library at authoring time and then hard-coded,
so the suite stays standard-library-only and fails on drift. The full
repository suite passes (236 passed; the only failures are 5 pre-existing
cases that require a git checkout and executable bits — the verification
environment had a tarball, not a clone).

## What is deliberately not done

- **No test has been run on data.** P01-19.1–P01-19.4 (the runs
  themselves) stay *Todo* in the subtask register: T1 waits on P01-04
  (BUSCO baseline) and P01-11 (repair), T4 on P01-06, T10 on P01-11.
  `results.md` Tables 1–3 and 6 stay *Pending*.
- **P01-19.5 (minimum detectable effects) is not implemented.** The MDE
  depends on the actual n of each analysis, which does not exist yet;
  computing it now would require inventing counts.
- **T5–T7 belong to P01-18** and are out of scope here.
