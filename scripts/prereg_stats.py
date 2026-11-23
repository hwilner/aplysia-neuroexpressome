#!/usr/bin/env python3
"""Pre-registered statistical tests T1-T4 and T10 for P01 (AplyNeuroExpress).

This module implements, in the Python standard library only, the tests named
in `materials-and-methods.md` section 5.2 for issue P01-19:

- T1  BUSCO completeness, repaired vs Release 102: McNemar's test on the
      discordant ortholog pairs. The pre-registered decision rule is:
      fewer than 10 discordant pairs -> the test is skipped and only the
      difference in proportion (with its interval) is reported; fewer than
      25 -> the exact binomial form; otherwise the chi-square form with
      continuity correction. Effect size: the difference in proportion
      with a Wilson-based interval (Newcombe's paired method 10).
- T2  Median CDS length, paired loci: Wilcoxon signed-rank, exact p when
      n <= 25, tie-corrected normal approximation with continuity
      correction otherwise. Effect size: matched-pairs rank-biserial
      correlation. Assumption check: if no more than 20% of the paired
      differences are non-zero the test falls back to a sign-flip
      permutation test on the mean difference (10000 resamples, fixed
      seed). Pre-registered fallback interval: bootstrap BCa on the
      median difference (10000 resamples, fixed seed).
- T3  Exon count change, paired: identical machinery to T2.
- T4  Cross-annotation BUSCO (Aplysia vs Elysia vs Euprymna): chi-square
      on the 3x2 contingency table when every expected count is >= 5,
      Fisher-Freeman-Halton exact otherwise; pairwise Fisher exact tests
      as a post-hoc with Holm adjustment. If the exact enumeration is
      infeasible the comparison degrades to proportions with Wilson
      intervals, reported as descriptive -- that is the pre-registered
      fallback, not an error.
- T10 Protein identity of recovered models vs Release 102: Welch's t-test
      with Welch-Satterthwaite degrees of freedom. Effect size: Hedges' g.
      Fallback: Mann-Whitney U (tie-corrected normal approximation with
      continuity correction).

Every rule above is fixed here, before any analysis data exist; the module
has never seen a measured value. Nothing in this module estimates,
simulates, or imputes a result: it only computes statistics from counts
and vectors supplied by the caller.

Design decisions, made here rather than at analysis time:

- Randomness is always seeded. The default seed is P01_DEFAULT_SEED,
  documented in one place, so a re-run is byte-identical.
- The exact Wilcoxon distribution is computed by subset-sum enumeration
  over the (possibly tied, midranked) rank values, which is exact for
  ties as well as for distinct ranks; the n <= 25 cutoff comes from the
  pre-registration's step 6.
- Newcombe's method 10 is the Wilson-based interval for a difference of
  paired proportions: it reduces to the independent square-and-add form
  when the paired phi coefficient is zero, and it never collapses when a
  diagonal cell is empty. The pre-registration asks for "the difference
  in proportion with a Wilson interval"; method 10 is the paired form of
  that instruction.
- Two-sided Fisher p-values sum the probabilities of every table with
  the observed margins whose probability is at most the observed table's
  (the "probability ordering" definition, matching R's fisher.test).

The module is a library. The driver scripts that load the real BUSCO and
paired-locus tables and call these functions land with their analyses;
this module lands first so the tests can pin every decision rule before
results exist.
"""

import math
import random
from collections import Counter
from typing import Dict, List, NamedTuple, Optional, Sequence, Tuple

__all__ = [
    "P01_DEFAULT_SEED",
    "EXACT_WILCOXON_MAX_N",
    "MCNEMAR_SKIP_DISCORDANTS",
    "MCNEMAR_EXACT_DISCORDANTS",
    "MIN_NONZERO_FRACTION",
    "DEFAULT_RESAMPLES",
    "McNemarResult",
    "WilcoxonResult",
    "ChiSquareResult",
    "FisherExactResult",
    "CrossAnnotationResult",
    "WelchResult",
    "MannWhitneyResult",
    "PermutationResult",
    "BootstrapBCaResult",
    "mcnemar",
    "wilcoxon_signed_rank",
    "permutation_test_mean_difference",
    "bootstrap_bca_median_difference",
    "chi_square_contingency",
    "expected_counts",
    "fisher_exact_2x2",
    "fisher_freeman_halton",
    "cross_annotation_comparison",
    "holm_adjust",
    "welch_ttest",
    "hedges_g",
    "mann_whitney_u",
    "wilson_interval",
    "paired_proportion_difference",
    "normal_ppf",
    "chi2_sf",
    "student_t_sf",
    "TooManyTablesError",
]

# Fixed analysis constants. Each value is either dictated by the
# pre-registration (section and step noted) or, where the plan leaves the
# value open, chosen here once and documented, before any data exist.
P01_DEFAULT_SEED = 20261005  # P01 kickoff date; used for every resample.
EXACT_WILCOXON_MAX_N = 25  # section 5.1 step 6: exact p when n <= 25.
MCNEMAR_SKIP_DISCORDANTS = 10  # T1: skip the test below 10 discordants.
MCNEMAR_EXACT_DISCORDANTS = 25  # T1: exact binomial form below 25.
MIN_NONZERO_FRACTION = 0.20  # T2/T3 assumption check (section 5.2).
DEFAULT_RESAMPLES = 10000  # section 5.1 step 7 permutation count.
# Cap on Fisher-Freeman-Halton enumeration. With BUSCO-scale counts the
# pre-registered fallback (descriptive proportions with Wilson intervals)
# is the correct destination, so a cap is a guard, not an approximation.
MAX_FFH_TABLES = 10_000_000


class TooManyTablesError(RuntimeError):
    """Raised when Fisher-Freeman-Halton enumeration exceeds its cap.

    The pre-registered fallback for T4 in that situation is to report
    proportions with Wilson intervals and state that the comparison is
    descriptive; raising makes that fallback an explicit, logged event
    rather than a silent approximation.
    """


# --------------------------------------------------------------------------
# Special functions (standard-library only).
# --------------------------------------------------------------------------


def normal_ppf(p: float) -> float:
    """Inverse standard normal CDF (Acklam's rational approximation).

    Args:
        p: probability in (0, 1).

    Returns:
        The quantile x with Phi(x) = p.

    Raises:
        ValueError: if p is not strictly inside (0, 1).
    """
    if not 0.0 < p < 1.0:
        raise ValueError("normal_ppf requires 0 < p < 1")
    # Coefficients from P. J. Acklam's algorithm; max |error| ~ 1.15e-9.
    a = [
        -3.969683028665376e01,
        2.209460984245205e02,
        -2.759285104469687e02,
        1.383577518672690e02,
        -3.066479806614716e01,
        2.506628277459239e00,
    ]
    b = [
        -5.447609879822406e01,
        1.615858368580409e02,
        -1.556989798598866e02,
        6.680131188771972e01,
        -1.328068155288572e01,
    ]
    c = [
        -7.784894002430293e-03,
        -3.223964580411365e-01,
        -2.400758277161838e00,
        -2.549732539343734e00,
        4.374664141464968e00,
        2.938163982698783e00,
    ]
    d = [
        7.784695709041462e-03,
        3.224671290700398e-01,
        2.445134137142996e00,
        3.754408661907416e00,
    ]
    p_low, p_high = 0.02425, 1.0 - 0.02425
    if p < p_low:
        q = math.sqrt(-2.0 * math.log(p))
        x = (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0
        )
    elif p <= p_high:
        q = p - 0.5
        r = q * q
        x = (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / (
            ((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0
        )
    else:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        x = -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0
        )
    # Two Newton refinements bring the rational approximation (max error
    # ~1.15e-9) to machine precision.
    for _ in range(2):
        error = 0.5 * (1.0 + math.erf(x / math.sqrt(2.0))) - p
        x -= error / (math.exp(-x * x / 2.0) / math.sqrt(2.0 * math.pi))
    return x


def _gamma_lower_reg(a: float, x: float) -> float:
    """Regularized lower incomplete gamma P(a, x) via series expansion."""
    if x <= 0:
        return 0.0
    total = 1.0 / a
    term = total
    k = 0
    while k < 10000:
        k += 1
        term *= x / (a + k)
        total += term
        if abs(term) < abs(total) * 1e-15:
            break
    return total * math.exp(-x + a * math.log(x) - math.lgamma(a))


def _gamma_upper_reg(a: float, x: float) -> float:
    """Regularized upper incomplete gamma Q(a, x) via continued fraction."""
    tiny = 1e-300
    b = x + 1.0 - a
    c = 1.0 / tiny
    d = 1.0 / max(b, tiny) if b != 0 else 1.0 / tiny
    h = d
    for i in range(1, 10000):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < tiny:
            d = tiny
        c = b + an / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-15:
            break
    return math.exp(-x + a * math.log(x) - math.lgamma(a)) * h


def chi2_sf(x: float, df: int) -> float:
    """Survival function of the chi-square distribution.

    Args:
        x: statistic value (>= 0).
        df: degrees of freedom (>= 1).

    Returns:
        P(chi2_df >= x).
    """
    if x <= 0.0:
        return 1.0
    a = df / 2.0
    half = x / 2.0
    if half < a + 1.0:
        return 1.0 - _gamma_lower_reg(a, half)
    return _gamma_upper_reg(a, half)


def _beta_reg(x: float, a: float, b: float) -> float:
    """Regularized incomplete beta I_x(a, b) via continued fraction."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0

    def betacf(x_: float, a_: float, b_: float) -> float:
        tiny = 1e-300
        qab = a_ + b_
        qap = a_ + 1.0
        qam = a_ - 1.0
        c = 1.0
        d = 1.0 - qab * x_ / qap
        if abs(d) < tiny:
            d = tiny
        d = 1.0 / d
        h = d
        for m in range(1, 10000):
            m2 = 2 * m
            aa = m * (b_ - m) * x_ / ((qam + m2) * (a_ + m2))
            d = 1.0 + aa * d
            if abs(d) < tiny:
                d = tiny
            c = 1.0 + aa / c
            if abs(c) < tiny:
                c = tiny
            d = 1.0 / d
            h *= d * c
            aa = -(a_ + m) * (qab + m) * x_ / ((a_ + m2) * (qap + m2))
            d = 1.0 + aa * d
            if abs(d) < tiny:
                d = tiny
            c = 1.0 + aa / c
            if abs(c) < tiny:
                c = tiny
            d = 1.0 / d
            delta = d * c
            h *= delta
            if abs(delta - 1.0) < 1e-15:
                break
        return h

    front = math.exp(
        math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
        + a * math.log(x) + b * math.log(1.0 - x)
    )
    if x < (a + 1.0) / (a + b + 2.0):
        return front * betacf(x, a, b) / a
    return 1.0 - front * betacf(1.0 - x, b, a) / b


def student_t_sf(t: float, df: float) -> float:
    """One-sided survival function of Student's t distribution.

    Args:
        t: statistic value.
        df: degrees of freedom (> 0).

    Returns:
        P(T_df >= t).
    """
    if df <= 0:
        raise ValueError("df must be positive")
    if t == 0.0:
        return 0.5
    x = df / (df + t * t)
    ib = _beta_reg(x, df / 2.0, 0.5)
    return ib / 2.0 if t > 0 else 1.0 - ib / 2.0


def _binom_two_sided_exact(k: int, n: int) -> float:
    """Exact two-sided binomial test of p = 0.5 (probability ordering).

    Sums the probabilities of every outcome at most as probable as k
    successes out of n under p = 0.5. Identical to R's binom.test.
    """
    log_p_obs = math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1) - n * math.log(2.0)
    total = 0.0
    for i in range(n + 1):
        log_p_i = (
            math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1) - n * math.log(2.0)
        )
        if log_p_i <= log_p_obs + 1e-12:
            total += math.exp(log_p_i)
    return min(1.0, total)


# --------------------------------------------------------------------------
# Effect-size intervals for proportions.
# --------------------------------------------------------------------------


def wilson_interval(k: int, n: int, alpha: float = 0.05) -> Tuple[float, float]:
    """Wilson score interval for a binomial proportion.

    Args:
        k: successes.
        n: trials.
        alpha: significance level; the interval is at 1 - alpha.

    Returns:
        (lower, upper) bounds on the proportion.
    """
    if n <= 0:
        raise ValueError("n must be positive")
    z = normal_ppf(1.0 - alpha / 2.0)
    p = k / n
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2.0 * n)) / denom
    half = z * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def paired_proportion_difference(
    both: int, first_only: int, second_only: int, neither: int, alpha: float = 0.05
) -> Tuple[float, Tuple[float, float]]:
    """Difference of paired proportions with Newcombe's method 10 interval.

    This is the Wilson-based interval for a paired difference that the
    pre-registration names for T1 ("the difference in proportion with a
    Wilson interval"): it uses the Wilson intervals of the two arms and
    shrinks them by the paired phi coefficient, reducing to Newcombe's
    independent square-and-add form when the phi coefficient is zero.

    Args:
        both: pairs positive in both arms.
        first_only: pairs positive in the first arm only.
        second_only: pairs positive in the second arm only.
        neither: pairs positive in neither arm.
        alpha: significance level; the interval is at 1 - alpha.

    Returns:
        (difference, (lower, upper)) where difference = p_first - p_second.
    """
    n = both + first_only + second_only + neither
    if n <= 0:
        raise ValueError("no pairs supplied")
    p1 = (both + first_only) / n
    p2 = (both + second_only) / n
    diff = p1 - p2
    l1, u1 = wilson_interval(both + first_only, n, alpha)
    l2, u2 = wilson_interval(both + second_only, n, alpha)
    # Phi coefficient of the paired 2x2 table, floored at zero per
    # Newcombe's method 10 (a negative association widens the interval,
    # and flooring is the conservative direction for this design).
    denom = math.sqrt((both + first_only) * (second_only + neither)
                      * (both + second_only) * (first_only + neither))
    phi = 0.0
    if denom > 0:
        phi = max(0.0, (both * neither - first_only * second_only) / denom)
    d_low = math.sqrt(
        (p1 - l1) ** 2 - 2.0 * phi * (p1 - l1) * (u2 - p2) + (u2 - p2) ** 2
    )
    d_high = math.sqrt(
        (u1 - p1) ** 2 - 2.0 * phi * (u1 - p1) * (p2 - l2) + (p2 - l2) ** 2
    )
    return diff, (diff - d_low, diff + d_high)


# --------------------------------------------------------------------------
# T1 -- McNemar's test on paired binary outcomes.
# --------------------------------------------------------------------------


class McNemarResult(NamedTuple):
    """Result of the pre-registered T1 McNemar procedure."""

    discordants: int
    skipped: bool  # True when discordants < MCNEMAR_SKIP_DISCORDANTS.
    method: str  # "exact", "chi2_continuity", or "skipped".
    statistic: Optional[float]  # chi-square statistic; None for exact/skipped.
    p_value: Optional[float]  # None when skipped.
    difference: float  # p_first - p_second over all pairs.
    difference_interval: Tuple[float, float]  # Newcombe method 10.


def mcnemar(
    both: int, first_only: int, second_only: int, neither: int
) -> McNemarResult:
    """Run the pre-registered T1 McNemar decision procedure.

    Args:
        both: pairs positive in both arms.
        first_only: pairs positive in the first (e.g. repaired) arm only.
        second_only: pairs positive in the second (e.g. baseline) arm only.
        neither: pairs positive in neither arm.

    Returns:
        A McNemarResult. When the discordant count is below
        MCNEMAR_SKIP_DISCORDANTS the test is skipped per the
        pre-registration and only the difference with its interval is
        reported; below MCNEMAR_EXACT_DISCORDANTS the exact binomial form
        is used, otherwise the chi-square form with continuity correction.
    """
    b, c = first_only, second_only
    n_disc = b + c
    diff, interval = paired_proportion_difference(both, first_only, second_only, neither)
    if n_disc < MCNEMAR_SKIP_DISCORDANTS:
        return McNemarResult(n_disc, True, "skipped", None, None, diff, interval)
    if n_disc < MCNEMAR_EXACT_DISCORDANTS:
        p = _binom_two_sided_exact(min(b, c), n_disc)
        return McNemarResult(n_disc, False, "exact", None, p, diff, interval)
    stat = (abs(b - c) - 1.0) ** 2 / n_disc
    p = chi2_sf(stat, 1)
    return McNemarResult(n_disc, False, "chi2_continuity", stat, p, diff, interval)


# --------------------------------------------------------------------------
# T2 / T3 -- Wilcoxon signed-rank on paired differences, with fallbacks.
# --------------------------------------------------------------------------


class WilcoxonResult(NamedTuple):
    """Result of the pre-registered T2/T3 signed-rank procedure."""

    n_pairs: int  # Pairs supplied.
    n_nonzero: int  # Pairs with a non-zero difference (the tested n).
    w_plus: float  # Sum of ranks of positive differences.
    w_minus: float  # Sum of ranks of negative differences.
    method: str  # "exact", "normal_approx", or "permutation_fallback".
    statistic: Optional[float]  # z for the approximation; None otherwise.
    p_value: float
    rank_biserial_r: float  # (W+ - W-) / (W+ + W-).
    assumption_ok: bool  # Fraction of non-zero differences > 0.20.


def _midranks(values: Sequence[float]) -> List[float]:
    """Midranks of absolute values, ties sharing their average rank."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        mean_rank = (i + j + 2) / 2.0  # Ranks are 1-based.
        for k in range(i, j + 1):
            ranks[order[k]] = mean_rank
        i = j + 1
    return ranks


def _exact_signed_rank_p(w_plus: float, ranks: Sequence[float]) -> float:
    """Exact two-sided p for the signed-rank statistic by subset sums.

    Enumerates the distribution of W+ over all 2^n sign assignments as a
    subset-sum count over the (possibly tied) rank values. Midranks are
    doubled first so every rank is an integer; the result is exact for
    ties as well as for distinct ranks.
    """
    scaled = [int(round(2.0 * r)) for r in ranks]
    total = sum(scaled)
    observed = int(round(2.0 * w_plus))
    counts: Dict[int, int] = {0: 1}
    for r in scaled:
        updated = dict(counts)
        for s, c in counts.items():
            updated[s + r] = updated.get(s + r, 0) + c
        counts = updated
    low = min(observed, total - observed)
    tail = sum(c for s, c in counts.items() if s <= low)
    return min(1.0, 2.0 * tail / (2.0 ** len(scaled)))


def wilcoxon_signed_rank(
    differences: Sequence[float],
    seed: int = P01_DEFAULT_SEED,
    n_resamples: int = DEFAULT_RESAMPLES,
) -> WilcoxonResult:
    """Run the pre-registered T2/T3 Wilcoxon signed-rank procedure.

    Args:
        differences: paired differences (repaired minus baseline, in the
            project's sign convention); zero differences are dropped, per
            the pre-registration's assumption check.
        seed: seed for the permutation fallback.
        n_resamples: resamples for the permutation fallback.

    Returns:
        A WilcoxonResult. The method is exact when the non-zero count is
        at most EXACT_WILCOXON_MAX_N, the tie-corrected normal
        approximation with continuity correction above it, and -- when no
        more than 20% of differences are non-zero, the pre-registered
        assumption failure -- a sign-flip permutation test on the mean
        difference instead.
    """
    n_pairs = len(differences)
    nonzero = [d for d in differences if d != 0]
    n = len(nonzero)
    fraction_nonzero = n / n_pairs if n_pairs else 0.0
    assumption_ok = fraction_nonzero > MIN_NONZERO_FRACTION
    if n == 0:
        raise ValueError("all differences are zero; the signed-rank test is undefined")
    abs_diffs = [abs(d) for d in nonzero]
    ranks = _midranks(abs_diffs)
    w_plus = sum(r for r, d in zip(ranks, nonzero) if d > 0)
    w_minus = sum(r for r, d in zip(ranks, nonzero) if d < 0)
    rank_sum = w_plus + w_minus
    r_rb = (w_plus - w_minus) / rank_sum if rank_sum > 0 else 0.0
    if not assumption_ok:
        p = permutation_test_mean_difference(
            differences, seed=seed, n_resamples=n_resamples
        ).p_value
        return WilcoxonResult(n_pairs, n, w_plus, w_minus, "permutation_fallback",
                              None, p, r_rb, assumption_ok)
    if n <= EXACT_WILCOXON_MAX_N:
        p = _exact_signed_rank_p(w_plus, ranks)
        return WilcoxonResult(n_pairs, n, w_plus, w_minus, "exact", None, p, r_rb,
                              assumption_ok)
    # Tie-corrected normal approximation with continuity correction.
    tie_counts = Counter(abs_diffs)
    tie_term = sum(t ** 3 - t for t in tie_counts.values())
    var = (n * (n + 1) * (2 * n + 1) - tie_term / 2.0) / 24.0
    mean_w = n * (n + 1) / 4.0
    delta = w_plus - mean_w
    z = (abs(delta) - 0.5) / math.sqrt(var)
    if delta < 0:
        z = -z
    p = 2.0 * 0.5 * math.erfc(abs(z) / math.sqrt(2.0))
    return WilcoxonResult(n_pairs, n, w_plus, w_minus, "normal_approx", z,
                          min(1.0, p), r_rb, assumption_ok)


class PermutationResult(NamedTuple):
    """Result of a sign-flip permutation test on paired differences."""

    observed: float  # Observed mean difference.
    p_value: float  # Two-sided, add-one corrected.
    n_resamples: int


def permutation_test_mean_difference(
    differences: Sequence[float],
    seed: int = P01_DEFAULT_SEED,
    n_resamples: int = DEFAULT_RESAMPLES,
) -> PermutationResult:
    """Sign-flip permutation test on the mean of paired differences.

    The pre-registered assumption-failure route for T2/T3 (section 5.2)
    and the generic small-n route of section 5.1 step 7. Under the null,
    each pair's sign is exchangeable, so the resampling flips signs at
    random. The p-value is add-one corrected so it is never zero.

    Args:
        differences: paired differences.
        seed: RNG seed; fixed by default so a re-run is byte-identical.
        n_resamples: number of resamples (10000 per section 5.1 step 7).

    Returns:
        A PermutationResult with the observed mean and two-sided p.
    """
    values = list(differences)
    if not values:
        raise ValueError("no differences supplied")
    observed = sum(values) / len(values)
    rng = random.Random(seed)
    count = 1  # Add-one: the observed arrangement counts as extreme as itself.
    for _ in range(n_resamples):
        flipped = sum(d if rng.random() < 0.5 else -d for d in values) / len(values)
        if abs(flipped) >= abs(observed) - 1e-15:
            count += 1
    return PermutationResult(observed, count / (n_resamples + 1), n_resamples)


class BootstrapBCaResult(NamedTuple):
    """BCa bootstrap interval for the median of paired differences."""

    median: float
    interval: Tuple[float, float]
    n_resamples: int


def _median(values: Sequence[float]) -> float:
    """Median of a sequence."""
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def bootstrap_bca_median_difference(
    differences: Sequence[float],
    alpha: float = 0.05,
    seed: int = P01_DEFAULT_SEED,
    n_resamples: int = DEFAULT_RESAMPLES,
) -> BootstrapBCaResult:
    """BCa bootstrap confidence interval for the median paired difference.

    The pre-registered fallback interval for T2/T3. Resampling is over
    pairs (with replacement); the bias correction comes from the fraction
    of bootstrap medians below the sample median and the acceleration
    from the jackknife.

    Args:
        differences: paired differences.
        alpha: significance level; the interval is at 1 - alpha.
        seed: RNG seed; fixed by default so a re-run is byte-identical.
        n_resamples: number of bootstrap resamples.

    Returns:
        A BootstrapBCaResult.

    Raises:
        ValueError: if the interval is degenerate (all bootstrap medians
            equal, or the sample has fewer than two distinct values).
    """
    values = list(differences)
    n = len(values)
    if n < 2:
        raise ValueError("need at least two differences")
    observed = _median(values)
    rng = random.Random(seed)
    boot = []
    for _ in range(n_resamples):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        boot.append(_median(sample))
    below = sum(1 for b in boot if b < observed)
    if below == 0 or below == n_resamples:
        raise ValueError("degenerate bootstrap distribution; BCa is undefined")
    z0 = normal_ppf(below / n_resamples)
    # Jackknife acceleration.
    jack = [_median(values[:i] + values[i + 1:]) for i in range(n)]
    jack_mean = sum(jack) / n
    num = sum((jack_mean - j) ** 3 for j in jack)
    den = 6.0 * (sum((jack_mean - j) ** 2 for j in jack) ** 1.5)
    if den == 0:
        raise ValueError("degenerate jackknife distribution; BCa is undefined")
    accel = num / den
    z_lo = normal_ppf(alpha / 2.0)
    z_hi = normal_ppf(1.0 - alpha / 2.0)

    def adjust(z: float) -> float:
        return z0 + (z0 + z) / (1.0 - accel * (z0 + z))

    def norm_cdf(x: float) -> float:
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

    q_lo = min(max(norm_cdf(adjust(z_lo)), 0.0), 1.0)
    q_hi = min(max(norm_cdf(adjust(z_hi)), 0.0), 1.0)
    ordered = sorted(boot)
    m = len(ordered)

    def quantile(q: float) -> float:
        pos = q * (m - 1)
        base = int(pos)
        frac = pos - base
        if base + 1 < m:
            return ordered[base] + frac * (ordered[base + 1] - ordered[base])
        return ordered[base]

    return BootstrapBCaResult(observed, (quantile(q_lo), quantile(q_hi)), n_resamples)


# --------------------------------------------------------------------------
# T4 -- cross-annotation comparison of proportions.
# --------------------------------------------------------------------------


def expected_counts(table: Sequence[Sequence[int]]) -> List[List[float]]:
    """Expected counts of a contingency table under independence."""
    rows = [sum(row) for row in table]
    cols = [sum(table[i][j] for i in range(len(table))) for j in range(len(table[0]))]
    total = sum(rows)
    return [[rows[i] * cols[j] / total for j in range(len(cols))] for i in range(len(rows))]


class ChiSquareResult(NamedTuple):
    """Chi-square test on a contingency table."""

    statistic: float
    df: int
    p_value: float
    min_expected: float


def chi_square_contingency(table: Sequence[Sequence[int]]) -> ChiSquareResult:
    """Chi-square test of independence on an RxC contingency table.

    Args:
        table: rows of observed counts (at least 2x2).

    Returns:
        A ChiSquareResult with the statistic, degrees of freedom, p-value,
        and the smallest expected count (the pre-registered assumption
        check for T4).
    """
    expected = expected_counts(table)
    stat = 0.0
    min_exp = math.inf
    for i, row in enumerate(table):
        for j, obs in enumerate(row):
            exp = expected[i][j]
            min_exp = min(min_exp, exp)
            if exp > 0:
                stat += (obs - exp) ** 2 / exp
    df = (len(table) - 1) * (len(table[0]) - 1)
    return ChiSquareResult(stat, df, chi2_sf(stat, df), min_exp)


class FisherExactResult(NamedTuple):
    """Fisher's exact test on a 2x2 table."""

    odds_ratio: float
    p_value: float


def _log_hypergeom(a: int, r1: int, r2: int, c1: int, n: int) -> float:
    """Log probability of a 2x2 table with cell a under fixed margins."""
    return (
        math.lgamma(r1 + 1) + math.lgamma(n - r1 + 1)
        + math.lgamma(c1 + 1) + math.lgamma(n - c1 + 1)
        - math.lgamma(n + 1) - math.lgamma(a + 1)
        - math.lgamma(r1 - a + 1) - math.lgamma(c1 - a + 1)
        - math.lgamma(n - r1 - c1 + a + 1)
    )


def fisher_exact_2x2(a: int, b: int, c: int, d: int) -> FisherExactResult:
    """Fisher's exact test on a 2x2 table, two-sided.

    The two-sided p sums the probabilities of every table with the
    observed margins whose probability is at most the observed table's
    (probability ordering, matching R's fisher.test).

    Args:
        a, b: first row.
        c, d: second row.

    Returns:
        A FisherExactResult with the conditional odds-ratio estimate and
        the two-sided p-value.
    """
    r1, r2 = a + b, c + d
    c1 = a + c
    n = r1 + r2
    if n == 0:
        raise ValueError("empty table")
    log_p_obs = _log_hypergeom(a, r1, r2, c1, n)
    lo = max(0, c1 - r2)
    hi = min(r1, c1)
    p = 0.0
    for i in range(lo, hi + 1):
        log_p_i = _log_hypergeom(i, r1, r2, c1, n)
        if log_p_i <= log_p_obs + 1e-12:
            p += math.exp(log_p_i)
    if b * c > 0:
        odds = (a * d) / (b * c)
    elif a * d > 0:
        odds = math.inf
    else:
        odds = math.nan  # Both cross-products are zero; ratio undefined.
    return FisherExactResult(odds, min(1.0, p))


def _log_multinom_prob(table: Sequence[Sequence[int]]) -> float:
    """Log probability of an RxC table under fixed margins (multivariate
    hypergeometric)."""
    rows = [sum(row) for row in table]
    cols = [sum(table[i][j] for i in range(len(table))) for j in range(len(table[0]))]
    n = sum(rows)
    log_p = sum(math.lgamma(c + 1) for c in cols) - math.lgamma(n + 1)
    for i, row in enumerate(table):
        log_row = math.lgamma(rows[i] + 1) - sum(math.lgamma(v + 1) for v in row)
        log_p += log_row
    return log_p


def fisher_freeman_halton(
    table: Sequence[Sequence[int]], max_tables: int = MAX_FFH_TABLES
) -> float:
    """Fisher-Freeman-Halton exact test on an RxC table, two-sided.

    Enumerates every table with the observed margins and sums the
    probabilities of those at most as probable as the observed table.

    Args:
        table: rows of observed counts.
        max_tables: enumeration cap; exceeding it raises
            TooManyTablesError so the caller takes the pre-registered
            descriptive fallback instead of an approximation.

    Returns:
        The two-sided p-value.

    Raises:
        TooManyTablesError: if the enumeration exceeds max_tables.
    """
    observed = [list(row) for row in table]
    n_rows = len(observed)
    n_cols = len(observed[0])
    rows = [sum(row) for row in observed]
    cols = [sum(observed[i][j] for i in range(n_rows)) for j in range(n_cols)]
    log_p_obs = _log_multinom_prob(observed)
    total = 0.0
    seen = 0
    current = [[0] * n_cols for _ in range(n_rows)]

    def recurse(i: int, j: int) -> None:
        nonlocal total, seen
        if i == n_rows - 1:
            # The last row is fixed by the column margins.
            for jj in range(n_cols):
                remaining = cols[jj] - sum(current[ii][jj] for ii in range(n_rows - 1))
                if remaining < 0:
                    return
                current[i][jj] = remaining
            seen += 1
            if seen > max_tables:
                raise TooManyTablesError(
                    f"Fisher-Freeman-Halton enumeration exceeded {max_tables} tables"
                )
            log_p = _log_multinom_prob(current)
            if log_p <= log_p_obs + 1e-12:
                total += math.exp(log_p)
            return
        # Fill row i cell by cell; the last cell of each row is fixed by
        # the row margin.
        if j == n_cols - 1:
            current[i][j] = rows[i] - sum(current[i][:j])
            if current[i][j] < 0:
                return
            recurse(i + 1, 0)
            return
        row_remaining = rows[i] - sum(current[i][:j])
        col_remaining = cols[j] - sum(current[ii][j] for ii in range(i))
        for value in range(0, min(row_remaining, col_remaining) + 1):
            current[i][j] = value
            recurse(i, j + 1)

    recurse(0, 0)
    return min(1.0, total)


def holm_adjust(p_values: Sequence[float]) -> List[float]:
    """Holm step-down adjustment of a family of p-values.

    Args:
        p_values: the raw p-values.

    Returns:
        Adjusted p-values in the original order.
    """
    m = len(p_values)
    order = sorted(range(m), key=lambda i: p_values[i])
    adjusted = [0.0] * m
    running = 0.0
    for rank, idx in enumerate(order):
        running = max(running, (m - rank) * p_values[idx])
        adjusted[idx] = min(1.0, running)
    return adjusted


class CrossAnnotationResult(NamedTuple):
    """Result of the pre-registered T4 cross-annotation procedure."""

    method: str  # "chi_square", "fisher_freeman_halton", or "descriptive".
    statistic: Optional[float]
    df: Optional[int]
    p_value: Optional[float]
    min_expected: float
    posthoc: Optional[List[Tuple[str, FisherExactResult, float]]]
    # (pair label, raw Fisher result, Holm-adjusted p).


def cross_annotation_comparison(
    table: Sequence[Sequence[int]], labels: Sequence[str]
) -> CrossAnnotationResult:
    """Run the pre-registered T4 cross-annotation decision procedure.

    Args:
        table: Rx2 (or RxC) contingency table, one row per annotation
            (e.g. complete vs not-complete BUSCO counts).
        labels: row labels, used to name the post-hoc pairs.

    Returns:
        A CrossAnnotationResult. Chi-square when every expected count is
        at least 5; Fisher-Freeman-Halton otherwise; and when the exact
        enumeration is infeasible, method "descriptive" with no p-value,
        which is the pre-registered fallback for T4. Pairwise Fisher
        post-hocs with Holm adjustment accompany either test.
    """
    expected = expected_counts(table)
    min_exp = min(min(row) for row in expected)
    pairs: List[Tuple[str, FisherExactResult]] = []
    for i in range(len(table)):
        for j in range(i + 1, len(table)):
            sub = [table[i], table[j]]
            if len(sub[0]) == 2:
                res = fisher_exact_2x2(sub[0][0], sub[0][1], sub[1][0], sub[1][1])
            else:
                p = fisher_freeman_halton(sub)
                res = FisherExactResult(math.nan, p)
            pairs.append((f"{labels[i]} vs {labels[j]}", res))
    adjusted = holm_adjust([res.p_value for _, res in pairs])
    posthoc = [(label, res, adj) for (label, res), adj in zip(pairs, adjusted)]
    if min_exp >= 5.0:
        chi = chi_square_contingency(table)
        return CrossAnnotationResult("chi_square", chi.statistic, chi.df, chi.p_value,
                                     min_exp, posthoc)
    try:
        p = fisher_freeman_halton(table)
    except TooManyTablesError:
        return CrossAnnotationResult("descriptive", None, None, None, min_exp, None)
    return CrossAnnotationResult("fisher_freeman_halton", None, None, p, min_exp, posthoc)


# --------------------------------------------------------------------------
# T10 -- Welch's t-test on unpaired continuous outcomes, with fallback.
# --------------------------------------------------------------------------


class WelchResult(NamedTuple):
    """Welch's t-test with Welch-Satterthwaite degrees of freedom."""

    statistic: float
    df: float
    p_value: float
    hedges_g: float


def hedges_g(first: Sequence[float], second: Sequence[float]) -> float:
    """Hedges' g for the difference first minus second.

    Cohen's d on the pooled standard deviation with the small-sample
    correction J = 1 - 3 / (4 * df - 1), df = n1 + n2 - 2. The sign
    convention is fixed: positive means the first group is larger.

    Args:
        first: first group (in T10, the recovered models' identities).
        second: second group (in T10, the Release 102 models' identities).

    Returns:
        Hedges' g.

    Raises:
        ValueError: if either group has fewer than two values or the
            pooled variance is zero.
    """
    x, y = list(first), list(second)
    n1, n2 = len(x), len(y)
    if n1 < 2 or n2 < 2:
        raise ValueError("Hedges' g needs at least two values per group")
    m1, m2 = sum(x) / n1, sum(y) / n2
    v1 = sum((v - m1) ** 2 for v in x) / (n1 - 1)
    v2 = sum((v - m2) ** 2 for v in y) / (n2 - 1)
    df = n1 + n2 - 2
    pooled = math.sqrt(((n1 - 1) * v1 + (n2 - 1) * v2) / df)
    if pooled == 0:
        raise ValueError("pooled variance is zero; g is undefined")
    correction = 1.0 - 3.0 / (4.0 * df - 1.0)
    return (m1 - m2) / pooled * correction


def welch_ttest(first: Sequence[float], second: Sequence[float]) -> WelchResult:
    """Welch's t-test (unequal variances), two-sided.

    The pooled-variance variant is deliberately not offered: the
    pre-registration for T10 says not to use it.

    Args:
        first: first group.
        second: second group.

    Returns:
        A WelchResult with the statistic, Welch-Satterthwaite df, the
        two-sided p-value, and Hedges' g (sign: first minus second).
    """
    x, y = list(first), list(second)
    n1, n2 = len(x), len(y)
    if n1 < 2 or n2 < 2:
        raise ValueError("Welch's t-test needs at least two values per group")
    m1, m2 = sum(x) / n1, sum(y) / n2
    v1 = sum((v - m1) ** 2 for v in x) / (n1 - 1)
    v2 = sum((v - m2) ** 2 for v in y) / (n2 - 1)
    if v1 == 0 and v2 == 0:
        raise ValueError("both groups have zero variance; the test is undefined")
    se = math.sqrt(v1 / n1 + v2 / n2)
    t = (m1 - m2) / se
    df = (v1 / n1 + v2 / n2) ** 2 / (
        (v1 / n1) ** 2 / (n1 - 1) + (v2 / n2) ** 2 / (n2 - 1)
    )
    p = 2.0 * student_t_sf(abs(t), df)
    return WelchResult(t, df, p, hedges_g(x, y))


class MannWhitneyResult(NamedTuple):
    """Mann-Whitney U test, the T10 fallback."""

    u: float  # U for the first group.
    z: float
    p_value: float


def mann_whitney_u(first: Sequence[float], second: Sequence[float]) -> MannWhitneyResult:
    """Mann-Whitney U test, two-sided, tie-corrected normal approximation.

    The pre-registered fallback for T10. With thousands of values the
    normal approximation with continuity and tie corrections is the
    practical form; an exact small-sample variant can be added when the
    fallback is ever actually needed.

    Args:
        first: first group.
        second: second group.

    Returns:
        A MannWhitneyResult with U for the first group, the z statistic,
        and the two-sided p-value.
    """
    x, y = list(first), list(second)
    n1, n2 = len(x), len(y)
    if n1 == 0 or n2 == 0:
        raise ValueError("both groups must be non-empty")
    combined = [(v, 0) for v in x] + [(v, 1) for v in y]
    combined.sort(key=lambda item: item[0])
    ranks = [0.0] * len(combined)
    i = 0
    tie_counts: List[int] = []
    while i < len(combined):
        j = i
        while j + 1 < len(combined) and combined[j + 1][0] == combined[i][0]:
            j += 1
        mean_rank = (i + j + 2) / 2.0
        for k in range(i, j + 1):
            ranks[k] = mean_rank
        tie_counts.append(j - i + 1)
        i = j + 1
    rank_sum_x = sum(r for r, (_, group) in zip(ranks, combined) if group == 0)
    u1 = rank_sum_x - n1 * (n1 + 1) / 2.0
    mean_u = n1 * n2 / 2.0
    n = n1 + n2
    tie_term = sum(t ** 3 - t for t in tie_counts)
    var = (n1 * n2 / 12.0) * ((n + 1) - tie_term / (n * (n - 1)))
    delta = u1 - mean_u
    z = (abs(delta) - 0.5) / math.sqrt(var)
    if delta < 0:
        z = -z
    p = math.erfc(abs(z) / math.sqrt(2.0))
    return MannWhitneyResult(u1, z, min(1.0, p))
