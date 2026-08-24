"""
Turn-order balance analysis (same-model, skill-neutral self-play games).

Reproduces the statistical tests reported in the paper's Results (turn-order
balance) and Appendix (statistical methodology):
  - A binomial test on P1 vs. P2 wins among decisive (non-drawn) games,
    against the null of "no difference."
  - A paired t-test and Wilcoxon signed-rank test on the per-game P1-P2
    score difference, against the null of "no difference." P1 and P2 scores
    come from the same match (same shared deck, same board) and are
    therefore paired observations, not independent samples — an earlier
    version of this script used Welch's t-test and Mann-Whitney U (treating
    the two score samples as independent), which a cross-model referee
    review flagged as the wrong test for this design. Fixed here.
  - A TOST (two one-sided tests) equivalence test on both the win-rate and
    the score difference, against a pre-specified margin of practical
    balance. A non-significant result on the tests above only means we
    failed to reject "no difference" — it does not itself demonstrate
    equivalence. The equivalence margin is ±10 percentage points on win
    rate (a designer's judgment call about what counts as a practically
    fair turn order) and ±0.2 pooled-SD on score (a conventional small-effect
    threshold, in raw points; kept in raw points computed from the pooled
    SD of the two samples even for the paired TOST, so the practical-
    significance threshold means the same thing regardless of which test
    evaluates it).

Because same-model games place an identical model on both seats, any
systematic P1-vs-P2 asymmetry here is attributable to the game's turn-order
design, not to a skill difference between the two AI models.
"""

import csv
import glob
import numpy as np
from scipy import stats
from statsmodels.stats.weightstats import ttost_paired

DATA_DIR = "results/cluster_runs"

WIN_RATE_MARGIN = 0.10   # +/- 10 percentage points around 50%
SCORE_EFFECT_SIZE_MARGIN = 0.2  # Cohen's d, converted to raw points via pooled SD


def to_float(v, default=0.0):
    try:
        return float(v)
    except (ValueError, TypeError):
        return default


def load_same_model_rows():
    rows = []
    for fpath in sorted(glob.glob(f"{DATA_DIR}/hvh_same_*.csv")):
        if "_details" in fpath or "_trace" in fpath:
            continue
        mode = "resistance" if "resistance" in fpath else "capacitance"
        with open(fpath) as fh:
            for row in csv.DictReader(fh):
                row["mode"] = mode
                rows.append(row)
    return rows


def one_sample_prop_tost(successes, n, null=0.5, low=-WIN_RATE_MARGIN, upp=WIN_RATE_MARGIN, alpha=0.05):
    """TOST for one proportion vs a null value, equivalence region [null+low, null+upp]."""
    p_hat = successes / n
    se = np.sqrt(p_hat * (1 - p_hat) / n)
    z_low = (p_hat - null - low) / se
    p_low = 1 - stats.norm.cdf(z_low)
    z_upp = (p_hat - null - upp) / se
    p_upp = stats.norm.cdf(z_upp)
    equivalent = (p_low < alpha) and (p_upp < alpha)
    return p_hat, p_low, p_upp, equivalent


def analyze_mode(rows, mode):
    mode_rows = [r for r in rows if r["mode"] == mode]
    n = len(mode_rows)
    p1_wins = sum(1 for r in mode_rows if r["winner"] == "P1")
    p2_wins = sum(1 for r in mode_rows if r["winner"] == "P2")
    draws = n - p1_wins - p2_wins
    decisive = p1_wins + p2_wins

    binom = stats.binomtest(p1_wins, decisive, 0.5, alternative="two-sided")
    chi2, chi_p = stats.chisquare([p1_wins, p2_wins], f_exp=[decisive / 2, decisive / 2])

    p1_scores = np.array([to_float(r["p1_score"]) for r in mode_rows])
    p2_scores = np.array([to_float(r["p2_score"]) for r in mode_rows])
    diffs = p1_scores - p2_scores
    corr = np.corrcoef(p1_scores, p2_scores)[0, 1]

    # Paired tests (correct: P1/P2 scores share a match, a deck, a board)
    t_stat, t_p = stats.ttest_1samp(diffs, 0)
    w_stat, w_p = stats.wilcoxon(diffs)

    print(f"=== {mode} (n={n} games, {decisive} decisive, {draws} draws) ===")
    print(f"  P1 win rate among decisive: {p1_wins}/{decisive} = {p1_wins/decisive:.1%}")
    print(f"  Binomial test vs 50%: p = {binom.pvalue:.5f}")
    print(f"  Chi-square (P1 vs P2 wins): chi2={chi2:.3f}, p={chi_p:.5f}")
    print(f"  P1 avg score = {p1_scores.mean():.1f}, P2 avg score = {p2_scores.mean():.1f}, "
          f"corr(P1,P2)={corr:.3f}")
    print(f"  Score paired t-test (on per-game P1-P2 diff): t={t_stat:.3f}, p={t_p:.5f}")
    print(f"  Score Wilcoxon signed-rank (paired): W={w_stat:.1f}, p={w_p:.5f}")

    p_hat, p_low, p_upp, equiv = one_sample_prop_tost(p1_wins, decisive)
    print(f"  Win-rate TOST (equivalence margin 50%+/-{WIN_RATE_MARGIN:.0%}): "
          f"lower-test p={p_low:.5f}, upper-test p={p_upp:.5f}, EQUIVALENT={equiv}")

    pooled_sd = np.sqrt((np.var(p1_scores, ddof=1) + np.var(p2_scores, ddof=1)) / 2)
    margin = SCORE_EFFECT_SIZE_MARGIN * pooled_sd
    tost_p, _, _ = ttost_paired(p1_scores, p2_scores, -margin, margin)
    print(f"  Score TOST, paired (equivalence margin +/-{margin:.2f} pts, Cohen's d={SCORE_EFFECT_SIZE_MARGIN}): "
          f"p={tost_p:.5f}, EQUIVALENT={tost_p < 0.05}")
    print()


if __name__ == "__main__":
    rows = load_same_model_rows()
    for mode in ["resistance", "capacitance"]:
        analyze_mode(rows, mode)
