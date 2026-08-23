"""
Turn-order balance analysis (same-model, skill-neutral self-play games).

Reproduces the statistical tests reported in the paper's Results (turn-order
balance) and Appendix (statistical methodology): a binomial test and
chi-square goodness-of-fit test on P1 vs. P2 wins among decisive (non-drawn)
games, plus Welch's t-test and Mann-Whitney U on the P1/P2 score difference,
computed separately for the resistance and capacitance modules.

Because same-model games place an identical model on both seats, any
systematic P1-vs-P2 asymmetry here is attributable to the game's turn-order
design, not to a skill difference between the two AI models.
"""

import csv
import glob
from scipy import stats

DATA_DIR = "results/cluster_runs"


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


def analyze_mode(rows, mode):
    mode_rows = [r for r in rows if r["mode"] == mode]
    n = len(mode_rows)
    p1_wins = sum(1 for r in mode_rows if r["winner"] == "P1")
    p2_wins = sum(1 for r in mode_rows if r["winner"] == "P2")
    draws = n - p1_wins - p2_wins
    decisive = p1_wins + p2_wins

    binom = stats.binomtest(p1_wins, decisive, 0.5, alternative="two-sided")
    chi2, chi_p = stats.chisquare([p1_wins, p2_wins], f_exp=[decisive / 2, decisive / 2])

    p1_scores = [to_float(r["p1_score"]) for r in mode_rows]
    p2_scores = [to_float(r["p2_score"]) for r in mode_rows]
    t_stat, t_p = stats.ttest_ind(p1_scores, p2_scores, equal_var=False)
    u_stat, u_p = stats.mannwhitneyu(p1_scores, p2_scores, alternative="two-sided")

    print(f"=== {mode} (n={n} games, {decisive} decisive, {draws} draws) ===")
    print(f"  P1 win rate among decisive: {p1_wins}/{decisive} = {p1_wins/decisive:.1%}")
    print(f"  Binomial test vs 50%: p = {binom.pvalue:.5f}")
    print(f"  Chi-square (P1 vs P2 wins): chi2={chi2:.3f}, p={chi_p:.5f}")
    print(f"  P1 avg score = {sum(p1_scores)/n:.1f}, P2 avg score = {sum(p2_scores)/n:.1f}")
    print(f"  Score Welch's t-test: t={t_stat:.3f}, p={t_p:.5f}")
    print(f"  Score Mann-Whitney U: U={u_stat:.1f}, p={u_p:.5f}")
    print()


if __name__ == "__main__":
    rows = load_same_model_rows()
    for mode in ["resistance", "capacitance"]:
        analyze_mode(rows, mode)
