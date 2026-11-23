#!/usr/bin/env python3
"""Tests for scripts/prereg_stats.py.

The reference values in this file are fixed before any analysis data
exist, and none of them comes from running the implementation under
test: the small cases are computed by hand or by exact enumeration, and
the larger ones were cross-checked once against an independent,
widely-audited statistics library (SciPy 1.16) at authoring time and
then hard-coded here, so the suite stays standard-library-only and fails
if the implementation drifts. The Fisher-Freeman-Halton reference was
verified by brute-force enumeration of all 26 tables with the observed
margins.

Run them with:

    python3 -m unittest discover -s tests
"""

import itertools
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir, "scripts"))

import prereg_stats as ps


class SpecialFunctionsTest(unittest.TestCase):
    """The normal, chi-square and Student-t machinery everything uses."""

    def test_normal_ppf(self):
        self.assertAlmostEqual(ps.normal_ppf(0.975), 1.9599639845400536, places=9)
        self.assertAlmostEqual(ps.normal_ppf(0.5), 0.0, places=12)
        self.assertAlmostEqual(ps.normal_ppf(0.025), -1.9599639845400536, places=9)

    def test_normal_ppf_rejects_endpoints(self):
        for bad in (0.0, 1.0, -0.1, 1.1):
            with self.assertRaises(ValueError):
                ps.normal_ppf(bad)

    def test_chi2_sf(self):
        # chi2_1 survival at 3.84 is just above 0.05 by construction of
        # the 1.96-squared threshold.
        self.assertAlmostEqual(ps.chi2_sf(3.84, 1), 0.05004352124870519, places=12)
        self.assertAlmostEqual(ps.chi2_sf(0.0, 2), 1.0, places=12)

    def test_student_t_sf(self):
        self.assertAlmostEqual(ps.student_t_sf(2.0, 10), 0.036694017385370196, places=12)
        self.assertAlmostEqual(ps.student_t_sf(0.0, 5), 0.5, places=15)


class McNemarTest(unittest.TestCase):
    """T1: the pre-registered McNemar decision procedure."""

    def test_exact_form_below_25_discordants(self):
        # 9 vs 1 discordant: two-sided binomial p = 2 * (C(10,0)+C(10,1))
        # / 2^10 = 22/1024, computed by hand.
        result = ps.mcnemar(both=50, first_only=9, second_only=1, neither=100)
        self.assertEqual(result.method, "exact")
        self.assertFalse(result.skipped)
        self.assertAlmostEqual(result.p_value, 0.021484375, places=15)
        self.assertIsNone(result.statistic)

    def test_chi2_form_at_25_or_more_discordants(self):
        # 30 vs 10 discordant: (|30-10|-1)^2 / 40 = 9.025.
        result = ps.mcnemar(both=50, first_only=30, second_only=10, neither=100)
        self.assertEqual(result.method, "chi2_continuity")
        self.assertAlmostEqual(result.statistic, 9.025, places=12)
        self.assertAlmostEqual(result.p_value, 0.002663119259138558, places=12)

    def test_skipped_below_10_discordants(self):
        # The pre-registration: fewer than 10 discordant pairs -> no test,
        # only the difference with its interval is reported.
        result = ps.mcnemar(both=50, first_only=5, second_only=2, neither=100)
        self.assertTrue(result.skipped)
        self.assertEqual(result.method, "skipped")
        self.assertIsNone(result.p_value)
        self.assertAlmostEqual(result.difference, (55 - 52) / 157, places=12)

    def test_difference_and_interval_are_paired(self):
        # Independent of which branch the test takes, the difference and
        # its Newcombe method-10 interval are always reported.
        result = ps.mcnemar(both=10, first_only=5, second_only=4, neither=2)
        diff, (lo, hi) = ps.paired_proportion_difference(10, 5, 4, 2)
        self.assertAlmostEqual(diff, 0.04761904761904767, places=15)
        self.assertAlmostEqual(lo, -0.22029324514698218, places=12)
        self.assertAlmostEqual(hi, 0.30669176616449023, places=12)
        self.assertAlmostEqual(result.difference, diff, places=15)

    def test_newcombe_reduces_to_independent_when_phi_is_zero(self):
        # With a*d == b*c the paired phi coefficient is zero and method 10
        # must reduce to the square-and-add of the two Wilson intervals.
        diff, (lo, hi) = ps.paired_proportion_difference(10, 5, 4, 2)
        l1, u1 = ps.wilson_interval(15, 21)
        l2, u2 = ps.wilson_interval(14, 21)
        p1, p2 = 15 / 21, 14 / 21
        self.assertAlmostEqual(lo, diff - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2),
                               places=12)
        self.assertAlmostEqual(hi, diff + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2),
                               places=12)

    def test_newcombe_narrows_under_positive_correlation(self):
        # Moving mass onto the diagonal (positive phi) must narrow the
        # interval relative to the uncorrelated case above.
        _, (lo_c, hi_c) = ps.paired_proportion_difference(12, 4, 3, 2)
        _, (lo_u, hi_u) = ps.paired_proportion_difference(10, 5, 4, 2)
        self.assertLess(hi_c - lo_c, hi_u - lo_u)


class WilsonTest(unittest.TestCase):
    """Wilson score intervals, the effect-size companion for proportions."""

    def test_known_interval(self):
        lo, hi = ps.wilson_interval(10, 100)
        self.assertAlmostEqual(lo, 0.055229137060675094, places=12)
        self.assertAlmostEqual(hi, 0.17436566150491345, places=12)

    def test_degenerate_counts_stay_in_bounds(self):
        lo, hi = ps.wilson_interval(0, 50)
        self.assertEqual(lo, 0.0)
        self.assertGreater(hi, 0.0)
        lo, hi = ps.wilson_interval(50, 50)
        self.assertEqual(hi, 1.0)
        self.assertLess(lo, 1.0)


class WilcoxonTest(unittest.TestCase):
    """T2/T3: signed-rank with the pre-registered exact/approx/fallback."""

    PAIRS_X = [3.1, 1.2, 0.5, 2.2, 1.8, 0.9, 2.7, 1.5, 0.4, 2.9, 1.1, 2.0, 0.7, 1.6]
    PAIRS_Y = [2.9, 1.5, 0.3, 2.0, 1.9, 1.2, 2.5, 1.4, 0.6, 2.4, 1.3, 1.8, 0.9, 1.7]
    # Fourteen differences with fourteen distinct absolute values.
    DISTINCT_DIFFS = [0.11, -0.29, 0.13, 0.31, -0.37, 0.17, 0.41,
                      -0.43, 0.47, -0.53, 0.59, -0.61, 0.67, 0.71]

    def test_exact_p_at_or_below_25_nonzero(self):
        # Distinct ranks: the exact p matches the standard reference
        # implementation's exact mode (0.463134765625) to machine
        # precision.
        result = ps.wilcoxon_signed_rank(self.DISTINCT_DIFFS)
        self.assertEqual(result.method, "exact")
        self.assertEqual(result.n_nonzero, 14)
        self.assertAlmostEqual(result.p_value, 0.463134765625, places=12)

    def test_exact_p_is_exact_for_ties_too(self):
        # The PAIRS differences carry tied absolute values (0.2, 0.3 and
        # 0.1 each recur), where the distinct-rank generating function is
        # not valid; the subset-sum enumeration over midranks is. The
        # reference 0.7005615234375 was verified by brute-force
        # enumeration of all 2^14 sign assignments, and the distinct-rank
        # formula's 0.71484375 on the same data is the wrong value, kept
        # here only as a comment so nobody "fixes" the implementation to
        # match it.
        diffs = [x - y for x, y in zip(self.PAIRS_X, self.PAIRS_Y)]
        result = ps.wilcoxon_signed_rank(diffs)
        self.assertEqual(result.method, "exact")
        self.assertAlmostEqual(result.p_value, 0.7005615234375, places=12)

    def test_exact_enumeration_matches_brute_force(self):
        # Independent check: enumerate all 2^6 sign assignments directly.
        diffs = [2.0, 1.0, 3.0, 0.5, 1.5, 2.5]
        ranks_total = sum(range(1, 7))
        w_obs = sum(r for r, d in zip(range(1, 7), diffs) if d > 0)
        low = min(w_obs, ranks_total - w_obs)
        extreme = 0
        for signs in itertools.product([0.0, 1.0], repeat=6):
            w = sum(s * r for s, r in zip(signs, range(1, 7)))
            if w <= low:
                extreme += 1
        expected_p = min(1.0, 2 * extreme / 2 ** 6)
        self.assertAlmostEqual(ps.wilcoxon_signed_rank(diffs).p_value, expected_p,
                               places=15)

    def test_normal_approximation_with_ties_above_25(self):
        xs = [1.7, -0.5, 0.0, 0.4, -0.8, 0.0, -0.0, -1.8, 1.0, 0.6, -0.6, -0.2,
              0.5, -0.3, -0.2, -1.5, 0.6, 0.1, 0.3, -1.5, 1.7, 0.2, -0.4, 2.0,
              -0.0, -1.5, -0.4, -2.3, 1.0, -0.4, -0.7, 1.1, -1.7, 0.5, -2.1,
              -0.7, -1.2, 1.5, 1.8, -0.3]
        ys = [1.0, 0.0, 0.8, -0.6, -1.5, -1.6, 0.6, 2.4, 0.5, -0.3, 2.1, 0.4,
              0.3, 0.5, 0.1, -0.1, -1.2, 0.7, 0.1, 1.4, -0.2, -1.7, 0.1, 1.9,
              -0.2, -0.7, -1.0, -0.9, -0.1, -1.0, 1.7, -0.1, 0.3, 1.6, 1.7,
              -0.0, 0.5, 0.9, 0.0, -1.6]
        diffs = [x - y for x, y in zip(xs, ys)]
        result = ps.wilcoxon_signed_rank(diffs)
        self.assertEqual(result.method, "normal_approx")
        self.assertAlmostEqual(result.p_value, 0.4928487005005012, places=9)

    def test_rank_biserial_by_construction(self):
        # All differences positive: every rank on the positive side.
        result = ps.wilcoxon_signed_rank([1.0, 2.0, 3.0, 4.0, 5.0])
        self.assertAlmostEqual(result.rank_biserial_r, 1.0, places=15)
        result = ps.wilcoxon_signed_rank([-1.0, -2.0, -3.0, -4.0, -5.0])
        self.assertAlmostEqual(result.rank_biserial_r, -1.0, places=15)

    def test_zero_differences_are_dropped(self):
        result = ps.wilcoxon_signed_rank([0.0, 0.0, 1.0, 2.0, -1.0])
        self.assertEqual(result.n_pairs, 5)
        self.assertEqual(result.n_nonzero, 3)

    def test_assumption_failure_routes_to_permutation(self):
        # 30 pairs, 4 non-zero differences: 4/30 <= 0.20 violates the
        # pre-registered assumption check, so the method must be the
        # permutation fallback, not a signed-rank p.
        diffs = [0.0] * 26 + [1.0, -2.0, 1.5, -0.5]
        result = ps.wilcoxon_signed_rank(diffs)
        self.assertFalse(result.assumption_ok)
        self.assertEqual(result.method, "permutation_fallback")
        self.assertIsNone(result.statistic)

    def test_all_zero_differences_rejected(self):
        with self.assertRaises(ValueError):
            ps.wilcoxon_signed_rank([0.0, 0.0, 0.0])


class PermutationFallbackTest(unittest.TestCase):
    """The sign-flip permutation test on the mean paired difference."""

    def test_monte_carlo_approaches_exact_enumeration(self):
        # Four differences: enumerate all 16 sign assignments by hand.
        diffs = [2.0, -1.0, 3.0, 4.0]
        observed = abs(sum(diffs) / 4)
        extreme = sum(
            1
            for signs in itertools.product([1, -1], repeat=4)
            if abs(sum(s * d for s, d in zip(signs, diffs)) / 4) >= observed - 1e-15
        )
        exact_p = extreme / 16
        result = ps.permutation_test_mean_difference(diffs, n_resamples=200000)
        self.assertAlmostEqual(result.p_value, exact_p, delta=0.005)

    def test_deterministic_under_fixed_seed(self):
        diffs = [2.0, -1.0, 3.0, 4.0, -2.5]
        first = ps.permutation_test_mean_difference(diffs)
        second = ps.permutation_test_mean_difference(diffs)
        self.assertEqual(first, second)

    def test_p_value_is_never_zero(self):
        # Add-one correction: even a maximally extreme observation has
        # p = 1 / (n_resamples + 1).
        result = ps.permutation_test_mean_difference([10.0, 11.0, 12.0],
                                                     n_resamples=1000)
        self.assertGreaterEqual(result.p_value, 1.0 / 1001.0)


class BootstrapBCaTest(unittest.TestCase):
    """The pre-registered T2/T3 fallback interval."""

    def test_deterministic_and_contains_median(self):
        diffs = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        first = ps.bootstrap_bca_median_difference(diffs, n_resamples=2000)
        second = ps.bootstrap_bca_median_difference(diffs, n_resamples=2000)
        self.assertEqual(first, second)
        self.assertEqual(first.median, 5.5)
        self.assertLessEqual(first.interval[0], 5.5)
        self.assertGreaterEqual(first.interval[1], 5.5)

    def test_degenerate_sample_rejected(self):
        # Every value identical: the bootstrap distribution has no spread
        # and the BCa correction is undefined; fail loudly, never guess.
        with self.assertRaises(ValueError):
            ps.bootstrap_bca_median_difference([3.0, 3.0, 3.0, 3.0])

    def test_too_few_values_rejected(self):
        with self.assertRaises(ValueError):
            ps.bootstrap_bca_median_difference([1.0])


class CrossAnnotationTest(unittest.TestCase):
    """T4: chi-square, Fisher-Freeman-Halton, post-hoc Holm, fallbacks."""

    def test_chi_square_route_when_expected_counts_adequate(self):
        result = ps.cross_annotation_comparison(
            [[700, 300], [650, 350], [800, 200]], ["Aplysia", "Elysia", "Euprymna"]
        )
        self.assertEqual(result.method, "chi_square")
        self.assertAlmostEqual(result.statistic, 57.45554035567716, places=9)
        self.assertEqual(result.df, 2)
        self.assertAlmostEqual(result.p_value, 3.339549878812084e-13, places=15)
        self.assertAlmostEqual(result.min_expected, 283.3333333333333, places=9)

    def test_exact_route_when_an_expected_count_is_small(self):
        result = ps.cross_annotation_comparison(
            [[6, 2], [1, 4], [0, 3]], ["Aplysia", "Elysia", "Euprymna"]
        )
        self.assertEqual(result.method, "fisher_freeman_halton")
        self.assertLess(result.min_expected, 5.0)

    def test_fisher_freeman_halton_matches_brute_force(self):
        # Enumerate all 26 tables with margins (8, 8) x (7, 6, 3) by hand
        # and sum those at most as probable as the observed table.
        table = [[6, 2, 0], [1, 4, 3]]

        def log_prob(t):
            rows = [8, 8]
            cols = [7, 6, 3]
            n = 16
            lp = sum(math.lgamma(c + 1) for c in cols) - math.lgamma(n + 1)
            for i, row in enumerate(t):
                lp += math.lgamma(rows[i] + 1) - sum(math.lgamma(v + 1) for v in row)
            return lp

        p_obs = math.exp(log_prob(table))
        total = 0.0
        for a in range(0, 8):
            for b in range(0, 8 - a + 1):
                c = 8 - a - b
                d, e = 7 - a, 6 - b
                if c > 3 or c < 0 or d < 0 or e < 0:
                    continue
                candidate = [[a, b, c], [d, e, 3 - c]]
                if log_prob(candidate) <= log_prob(table) + 1e-12:
                    total += math.exp(log_prob(candidate))
        self.assertEqual(p_obs, math.exp(log_prob(table)))
        self.assertAlmostEqual(ps.fisher_freeman_halton(table), total, places=10)
        self.assertAlmostEqual(ps.fisher_freeman_halton(table),
                               0.024242424242424253, places=12)

    def test_enumeration_cap_raises_for_descriptive_fallback(self):
        with self.assertRaises(ps.TooManyTablesError):
            ps.fisher_freeman_halton([[6, 2, 0], [1, 4, 3]], max_tables=1)
        # And the routed procedure then degrades to the pre-registered
        # descriptive fallback rather than approximating.
        result = ps.cross_annotation_comparison(
            [[6, 2], [1, 4], [0, 3]], ["A", "E", "U"]
        )
        self.assertIn(result.method, ("fisher_freeman_halton", "descriptive"))

    def test_posthoc_pairs_are_holm_adjusted(self):
        result = ps.cross_annotation_comparison(
            [[6, 2], [1, 4], [0, 3]], ["A", "E", "U"]
        )
        self.assertEqual(len(result.posthoc), 3)
        raw = [res.p_value for _, res, _ in result.posthoc]
        adjusted = [adj for _, _, adj in result.posthoc]
        self.assertEqual(adjusted, ps.holm_adjust(raw))
        for raw_p, adj_p in zip(raw, adjusted):
            self.assertGreaterEqual(adj_p, raw_p - 1e-15)

    def test_holm_known_answer(self):
        # Sorted 0.01, 0.03, 0.04 -> 0.01*3, 0.03*2, 0.04*1 with the
        # running maximum: 0.03, 0.06, 0.06.
        self.assertEqual(ps.holm_adjust([0.01, 0.04, 0.03]), [0.03, 0.06, 0.06])


class FisherExactTest(unittest.TestCase):
    """The 2x2 exact test used by T4 post-hocs and available to T7."""

    def test_tea_tasting_symmetry(self):
        # [[3,1],[1,3]]: tables 0..4 with probabilities 1/70, 16/70,
        # 36/70, 16/70, 1/70; two-sided = 34/70.
        result = ps.fisher_exact_2x2(3, 1, 1, 3)
        self.assertAlmostEqual(result.p_value, 34 / 70, places=12)
        self.assertAlmostEqual(result.odds_ratio, 9.0, places=12)

    def test_known_asymmetric_table(self):
        result = ps.fisher_exact_2x2(10, 2, 3, 15)
        self.assertAlmostEqual(result.p_value, 0.0005367241191434357, places=12)
        self.assertAlmostEqual(result.odds_ratio, 25.0, places=12)

    def test_large_counts_do_not_overflow(self):
        # BUSCO-scale counts: the log-domain computation must stay finite
        # where a naive combinatorial one would not.
        result = ps.fisher_exact_2x2(950, 50, 900, 100)
        self.assertTrue(math.isfinite(result.p_value))
        self.assertGreaterEqual(result.p_value, 0.0)
        self.assertLessEqual(result.p_value, 1.0)


class WelchTest(unittest.TestCase):
    """T10: Welch's t-test, Hedges' g, and the Mann-Whitney fallback."""

    FIRST = [5.1, 4.9, 6.2, 5.5, 4.7, 5.9, 6.0, 5.3, 4.8, 5.7]
    SECOND = [4.2, 3.8, 4.5, 4.0, 3.5, 4.8, 3.9, 4.1]

    def test_welch_known_answer(self):
        result = ps.welch_ttest(self.FIRST, self.SECOND)
        self.assertAlmostEqual(result.statistic, 5.9157733715245495, places=9)
        self.assertAlmostEqual(result.df, 15.985239958842941, places=9)
        self.assertAlmostEqual(result.p_value, 2.1811313190014987e-05, places=12)

    def test_hedges_g_sign_and_value(self):
        result = ps.welch_ttest(self.FIRST, self.SECOND)
        self.assertAlmostEqual(result.hedges_g, 2.5912753947422376, places=9)
        # The sign convention is fixed: first minus second.
        flipped = ps.welch_ttest(self.SECOND, self.FIRST)
        self.assertAlmostEqual(flipped.hedges_g, -result.hedges_g, places=12)

    def test_hedges_g_correction_by_construction(self):
        # [2,3,4] vs [1,2,3]: pooled SD 1, Cohen's d = 1, df = 4,
        # J = 1 - 3/15 = 0.8.
        self.assertAlmostEqual(ps.hedges_g([2, 3, 4], [1, 2, 3]), 0.8, places=12)

    def test_zero_variance_rejected(self):
        with self.assertRaises(ValueError):
            ps.welch_ttest([2.0, 2.0], [3.0, 3.0])

    def test_mann_whitney_known_answer(self):
        first = [12, 15, 14, 10, 13, 17, 11, 16, 14, 18, 9, 13, 15, 12, 14]
        second = [8, 11, 9, 12, 7, 10, 13, 6, 11, 9]
        result = ps.mann_whitney_u(first, second)
        self.assertAlmostEqual(result.u, 132.5, places=9)
        self.assertAlmostEqual(result.p_value, 0.0014970569494216891, places=9)


class DesignRulesTest(unittest.TestCase):
    """The fixed constants are the pre-registered ones."""

    def test_constants_match_the_preregistration(self):
        self.assertEqual(ps.EXACT_WILCOXON_MAX_N, 25)  # section 5.1 step 6
        self.assertEqual(ps.MCNEMAR_SKIP_DISCORDANTS, 10)  # T1
        self.assertEqual(ps.MCNEMAR_EXACT_DISCORDANTS, 25)  # T1
        self.assertEqual(ps.MIN_NONZERO_FRACTION, 0.20)  # T2/T3 check
        self.assertEqual(ps.DEFAULT_RESAMPLES, 10000)  # section 5.1 step 7
        self.assertEqual(ps.P01_DEFAULT_SEED, 20261005)


if __name__ == "__main__":
    unittest.main()
