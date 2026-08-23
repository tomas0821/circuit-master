"""
HvH Benchmark Analysis
Generates paper figures from the 1200-game HybridAgent vs HybridAgent benchmark.
Output: results/hvh_analysis/
"""

import csv
import glob
import os
import collections
import math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec

OUT_DIR = "results/hvh_analysis"
os.makedirs(OUT_DIR, exist_ok=True)

DATA_DIR = "results/cluster_runs"

# ── Model display names ───────────────────────────────────────────────────────
MODEL_NAMES = {
    "llama3.3:70b":   "Llama 3.3 70B",
    "qwen3:32b":      "Qwen3 32B",
    "mixtral:latest": "Mixtral 8×7B",
}
MODEL_SHORT = {
    "llama3.3:70b":   "Llama",
    "qwen3:32b":      "Qwen3",
    "mixtral:latest": "Mixtral",
}
MODEL_ORDER = ["llama3.3:70b", "qwen3:32b", "mixtral:latest"]
MODEL_COLORS = {
    "llama3.3:70b":   "#2166ac",
    "qwen3:32b":      "#1b7837",
    "mixtral:latest": "#d6604d",
}

# ── Load data ─────────────────────────────────────────────────────────────────
def load_all():
    """Returns list of dicts, one per game."""
    rows = []
    # Only use the final full-run jobs (35808–35819)
    for fpath in sorted(glob.glob(f"{DATA_DIR}/hvh_*.csv")):
        fname = os.path.basename(fpath)
        if "_details" in fname:
            continue
        # skip partial runs (35787-35789)
        job_id = int(fname.rstrip(".csv").split("_")[-1])
        if job_id < 35808:
            continue
        # infer mode from filename
        if "resistance" in fname:
            mode = "resistance"
        elif "capacitance" in fname:
            mode = "capacitance"
        else:
            mode = "unknown"
        # infer type
        if "hvh_same" in fname:
            kind = "same"
        else:
            kind = "cross"
        with open(fpath) as fh:
            for row in csv.DictReader(fh):
                row["mode"] = mode
                row["kind"] = kind
                rows.append(row)
    return rows

def to_int(v, default=0):
    try:
        return int(v)
    except (ValueError, TypeError):
        return default

def to_float(v, default=0.0):
    try:
        return float(v)
    except (ValueError, TypeError):
        return default

# ── Wilson confidence interval ────────────────────────────────────────────────
def wilson_ci(wins, n, z=1.96):
    if n == 0:
        return 0.5, 0.0, 1.0
    p = wins / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2*n)) / denom
    margin = (z * math.sqrt(p*(1-p)/n + z**2/(4*n**2))) / denom
    return centre, max(0, centre - margin), min(1, centre + margin)

# ═══════════════════════════════════════════════════════════════════════════════
# Figure 1: Cross-model win-rate heatmaps (resistance + capacitance)
# ═══════════════════════════════════════════════════════════════════════════════
def fig_winrate_matrix(rows):
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))

    for ax, mode in zip(axes, ["resistance", "capacitance"]):
        # Build win count matrix: matrix[row_model][col_model] = P1 win rate
        # P1 is the row model; P2 is the col model
        n_models = len(MODEL_ORDER)
        win_matrix = np.full((n_models, n_models), np.nan)
        count_matrix = np.zeros((n_models, n_models))

        for r in rows:
            if r["mode"] != mode or r["kind"] != "cross":
                continue
            m1 = r["p1_model"]
            m2 = r["p2_model"]
            if m1 not in MODEL_ORDER or m2 not in MODEL_ORDER:
                continue
            i = MODEL_ORDER.index(m1)
            j = MODEL_ORDER.index(m2)
            if np.isnan(win_matrix[i, j]):
                win_matrix[i, j] = 0
            count_matrix[i, j] += 1
            if r["winner"] == "P1":
                win_matrix[i, j] += 1

        # Convert to rates
        with np.errstate(invalid='ignore'):
            rate_matrix = win_matrix / count_matrix

        im = ax.imshow(rate_matrix, cmap="RdYlGn", vmin=0, vmax=1, aspect='auto')
        labels = [MODEL_SHORT[m] for m in MODEL_ORDER]
        ax.set_xticks(range(n_models))
        ax.set_yticks(range(n_models))
        ax.set_xticklabels(labels, fontsize=11)
        ax.set_yticklabels(labels, fontsize=11)
        ax.set_xlabel("Player 2 (P2)", fontsize=11)
        ax.set_ylabel("Player 1 (P1)", fontsize=11)
        ax.set_title(f"Win Rate — {mode.capitalize()}", fontsize=13, fontweight='bold')

        # Annotate cells
        for i in range(n_models):
            for j in range(n_models):
                val = rate_matrix[i, j]
                n = int(count_matrix[i, j])
                if np.isnan(val) or n == 0:
                    ax.text(j, i, "—", ha='center', va='center', fontsize=12, color='gray')
                else:
                    text_color = "white" if (val > 0.75 or val < 0.25) else "black"
                    ax.text(j, i, f"{val:.0%}\n(n={n})",
                            ha='center', va='center', fontsize=10,
                            color=text_color, fontweight='bold')

        plt.colorbar(im, ax=ax, label="P1 win rate")

    plt.suptitle("HybridAgent Cross-Model Win Rates", fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    fpath = f"{OUT_DIR}/fig1_winrate_matrix.pdf"
    plt.savefig(fpath, bbox_inches='tight', dpi=150)
    plt.savefig(fpath.replace('.pdf', '.png'), bbox_inches='tight', dpi=150)
    plt.close()
    print(f"Saved {fpath}")


# ═══════════════════════════════════════════════════════════════════════════════
# Figure 2: Score distributions per model (same-model games only)
# ═══════════════════════════════════════════════════════════════════════════════
def fig_score_distributions(rows):
    fig, axes = plt.subplots(1, 2, figsize=(11, 5))

    for ax, mode in zip(axes, ["resistance", "capacitance"]):
        scores_by_model = {m: [] for m in MODEL_ORDER}
        for r in rows:
            if r["mode"] != mode or r["kind"] != "same":
                continue
            m = r["p1_model"]  # same model, so p1_model == p2_model
            if m not in scores_by_model:
                continue
            scores_by_model[m].append(to_int(r["p1_score"]))
            scores_by_model[m].append(to_int(r["p2_score"]))

        positions = range(len(MODEL_ORDER))
        bp = ax.boxplot(
            [scores_by_model[m] for m in MODEL_ORDER],
            positions=list(positions),
            widths=0.5,
            patch_artist=True,
            medianprops=dict(color='black', linewidth=2),
            whiskerprops=dict(linewidth=1.5),
            capprops=dict(linewidth=1.5),
            flierprops=dict(marker='o', markersize=3, alpha=0.5),
        )
        for patch, model in zip(bp['boxes'], MODEL_ORDER):
            patch.set_facecolor(MODEL_COLORS[model])
            patch.set_alpha(0.75)

        # Overlay individual points (jittered)
        for pos, model in enumerate(MODEL_ORDER):
            data = scores_by_model[model]
            jitter = np.random.default_rng(42).uniform(-0.18, 0.18, len(data))
            ax.scatter(np.array([pos]*len(data)) + jitter, data,
                       alpha=0.25, s=8, color=MODEL_COLORS[model], zorder=5)

        ax.set_xticks(list(positions))
        ax.set_xticklabels([MODEL_SHORT[m] for m in MODEL_ORDER], fontsize=11)
        ax.set_ylabel("Score", fontsize=11)
        ax.set_title(f"Score Distribution — {mode.capitalize()}\n(same-model games, both players)",
                     fontsize=12, fontweight='bold')
        ax.grid(axis='y', alpha=0.3)
        ax.set_ylim(bottom=0)

    plt.tight_layout()
    fpath = f"{OUT_DIR}/fig2_score_distributions.pdf"
    plt.savefig(fpath, bbox_inches='tight', dpi=150)
    plt.savefig(fpath.replace('.pdf', '.png'), bbox_inches='tight', dpi=150)
    plt.close()
    print(f"Saved {fpath}")


# ═══════════════════════════════════════════════════════════════════════════════
# Figure 3: LLM reliability (API success rate & fallback rate per model)
# Computed live from the per-turn trace JSONL files (results/cluster_runs/*_trace.jsonl,
# jobs 35808-35819, pulled from ~/boardwalk/results/cluster_runs/ on the cluster on
# 2026-08-23). Falls back to a hardcoded snapshot (computed the same way, from the
# same 12 files, on 2026-08-23) if the trace files aren't present locally — they're
# ~28MB total and not committed to git.
# ═══════════════════════════════════════════════════════════════════════════════
_TRACE_STATS_SNAPSHOT_2026_08_23 = {
    "llama3.3:70b":   {"calls": 3950, "success": 3943, "fallback":    7, "avg_ms": 3987},
    "qwen3:32b":      {"calls": 3323, "success":    0, "fallback": 3323, "avg_ms": 5117},
    "mixtral:latest": {"calls": 2345, "success":  846, "fallback": 1499, "avg_ms": 1568},
}

def _compute_trace_stats():
    stats = {m: {"calls": 0, "success": 0, "fallback": 0, "_elapsed": []} for m in MODEL_ORDER}
    trace_files = sorted(glob.glob(f"{DATA_DIR}/*_trace.jsonl"))
    if not trace_files:
        print("No trace JSONL files found locally — using hardcoded 2026-08-23 snapshot for fig3.")
        return _TRACE_STATS_SNAPSHOT_2026_08_23
    import json
    for fpath in trace_files:
        with open(fpath) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                m = d.get("model")
                if m not in stats:
                    continue
                stats[m]["calls"] += 1
                if d.get("success"):
                    stats[m]["success"] += 1
                if d.get("fallback"):
                    stats[m]["fallback"] += 1
                if d.get("elapsed_ms") is not None:
                    stats[m]["_elapsed"].append(d["elapsed_ms"])
    for m, s in stats.items():
        elapsed = s.pop("_elapsed")
        s["avg_ms"] = round(sum(elapsed) / len(elapsed)) if elapsed else 0
    return stats

TRACE_STATS = _compute_trace_stats()

def fig_reliability(rows):
    models = MODEL_ORDER
    api_rates      = [TRACE_STATS[m]["success"] / TRACE_STATS[m]["calls"] for m in models]
    fallback_rates = [TRACE_STATS[m]["fallback"] / TRACE_STATS[m]["calls"] for m in models]

    x = np.arange(len(models))
    width = 0.35

    fig, ax = plt.subplots(figsize=(8, 5))
    bars1 = ax.bar(x - width/2, api_rates, width,
                   label="API success rate",
                   color=[MODEL_COLORS[m] for m in models], alpha=0.85)
    bars2 = ax.bar(x + width/2, fallback_rates, width,
                   label="Fallback rate",
                   color=[MODEL_COLORS[m] for m in models], alpha=0.45,
                   hatch='//')

    ax.set_ylabel("Rate", fontsize=12)
    ax.set_title("LLM Strategy Call Reliability\n(HybridAgent, same-model games)", fontsize=13, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([MODEL_SHORT[m] for m in models], fontsize=12)
    ax.set_ylim(0, 1.05)
    ax.legend(fontsize=11)
    ax.grid(axis='y', alpha=0.3)

    # Annotate bars
    for bar in bars1:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, h + 0.01,
                f"{h:.1%}", ha='center', va='bottom', fontsize=9)
    for bar in bars2:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, h + 0.01,
                f"{h:.1%}", ha='center', va='bottom', fontsize=9)

    # Add raw call counts as legend note
    for i, m in enumerate(models):
        ax.text(x[i], -0.08, f"n={TRACE_STATS[m]['calls']}", ha='center',
                va='top', fontsize=8.5, color='gray',
                transform=ax.get_xaxis_transform())

    # Qwen3 annotation
    ax.annotate("*thinking mode:\ncontent always empty",
                xy=(x[1] + width/2, fallback_rates[1]),
                xytext=(x[1] + 0.55, 0.75),
                fontsize=8.5, color='#666666',
                arrowprops=dict(arrowstyle='->', color='#888888', lw=1))

    plt.tight_layout()
    fpath = f"{OUT_DIR}/fig3_reliability.pdf"
    plt.savefig(fpath, bbox_inches='tight', dpi=150)
    plt.savefig(fpath.replace('.pdf', '.png'), bbox_inches='tight', dpi=150)
    plt.close()
    print(f"Saved {fpath}")


# ═══════════════════════════════════════════════════════════════════════════════
# Figure 4: Elo-style ranking bars with 95% Wilson CI
# ═══════════════════════════════════════════════════════════════════════════════
def fig_model_ranking(rows):
    """Win rate of each model as P1 across all cross-model games."""
    # Aggregate: for each model m, how often does it win when it plays as P1
    # against any opponent?
    win_vs = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0]))
    # win_vs[model][opponent] = [wins, total]
    for r in rows:
        if r["kind"] != "cross":
            continue
        m1, m2 = r["p1_model"], r["p2_model"]
        if m1 not in MODEL_ORDER or m2 not in MODEL_ORDER:
            continue
        win_vs[m1][m2][1] += 1
        win_vs[m2][m1][1] += 1
        if r["winner"] == "P1":
            win_vs[m1][m2][0] += 1
        elif r["winner"] == "P2":
            win_vs[m2][m1][0] += 1

    fig, axes = plt.subplots(1, 2, figsize=(11, 5))

    for ax, mode_filter in zip(axes, ["resistance", "capacitance"]):
        win_data = collections.defaultdict(lambda: [0, 0])
        for r in rows:
            if r["kind"] != "cross" or r["mode"] != mode_filter:
                continue
            m1, m2 = r["p1_model"], r["p2_model"]
            if m1 not in MODEL_ORDER or m2 not in MODEL_ORDER:
                continue
            win_data[m1][1] += 1
            win_data[m2][1] += 1
            if r["winner"] == "P1":
                win_data[m1][0] += 1
            elif r["winner"] == "P2":
                win_data[m2][0] += 1

        centres, lo_errs, hi_errs = [], [], []
        for m in MODEL_ORDER:
            wins, total = win_data[m]
            c, lo, hi = wilson_ci(wins, total)
            centres.append(c)
            lo_errs.append(c - lo)
            hi_errs.append(hi - c)

        x = np.arange(len(MODEL_ORDER))
        bars = ax.bar(x, centres, color=[MODEL_COLORS[m] for m in MODEL_ORDER],
                      alpha=0.82, width=0.5)
        ax.errorbar(x, centres, yerr=[lo_errs, hi_errs],
                    fmt='none', ecolor='black', capsize=5, elinewidth=1.5)
        ax.axhline(0.5, color='gray', linestyle='--', linewidth=1, alpha=0.7, label="50% baseline")

        for bar, m, c in zip(bars, MODEL_ORDER, centres):
            wins_n = win_data[m][0]
            total_n = win_data[m][1]
            ax.text(bar.get_x() + bar.get_width()/2, c + 0.02,
                    f"{c:.0%}\n({wins_n}/{total_n})",
                    ha='center', va='bottom', fontsize=9.5)

        ax.set_ylim(0, 1.1)
        ax.set_xticks(x)
        ax.set_xticklabels([MODEL_SHORT[m] for m in MODEL_ORDER], fontsize=12)
        ax.set_ylabel("Win rate (95% CI)", fontsize=11)
        ax.set_title(f"Cross-Model Win Rate — {mode_filter.capitalize()}",
                     fontsize=13, fontweight='bold')
        ax.legend(fontsize=10)
        ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    fpath = f"{OUT_DIR}/fig4_model_ranking.pdf"
    plt.savefig(fpath, bbox_inches='tight', dpi=150)
    plt.savefig(fpath.replace('.pdf', '.png'), bbox_inches='tight', dpi=150)
    plt.close()
    print(f"Saved {fpath}")


# ═══════════════════════════════════════════════════════════════════════════════
# Figure 5: Same-model balance (P1 first-move advantage check)
# ═══════════════════════════════════════════════════════════════════════════════
def fig_same_model_balance(rows):
    fig, axes = plt.subplots(1, 2, figsize=(11, 5))

    for ax, mode in zip(axes, ["resistance", "capacitance"]):
        p1_rates, lo_errs, hi_errs = [], [], []
        labels, draw_pcts = [], []
        for m in MODEL_ORDER:
            p1w = p2w = draws = 0
            for r in rows:
                if r["kind"] != "same" or r["mode"] != mode:
                    continue
                if r["p1_model"] != m:
                    continue
                if r["winner"] == "P1":
                    p1w += 1
                elif r["winner"] == "P2":
                    p2w += 1
                else:
                    draws += 1
            total = p1w + p2w + draws
            c, lo, hi = wilson_ci(p1w, total)
            p1_rates.append(c)
            lo_errs.append(c - lo)
            hi_errs.append(hi - c)
            labels.append(MODEL_SHORT[m])
            draw_pcts.append(draws / total if total > 0 else 0)

        x = np.arange(len(MODEL_ORDER))
        bars = ax.bar(x, p1_rates, color=[MODEL_COLORS[m] for m in MODEL_ORDER],
                      alpha=0.82, width=0.5)
        ax.errorbar(x, p1_rates, yerr=[lo_errs, hi_errs],
                    fmt='none', ecolor='black', capsize=5, elinewidth=1.5)
        ax.axhline(0.5, color='gray', linestyle='--', linewidth=1.5, alpha=0.8, label="50% baseline")
        ax.fill_between([-0.5, len(MODEL_ORDER)-0.5], [0.4, 0.4], [0.6, 0.6],
                        alpha=0.07, color='gray', label="±10% band")

        for bar, rate, dp in zip(bars, p1_rates, draw_pcts):
            ax.text(bar.get_x() + bar.get_width()/2, rate + 0.015,
                    f"{rate:.0%}", ha='center', va='bottom', fontsize=10.5)
            ax.text(bar.get_x() + bar.get_width()/2, 0.02,
                    f"draws={dp:.0%}", ha='center', va='bottom',
                    fontsize=8, color='#555555')

        ax.set_ylim(0, 0.95)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=12)
        ax.set_ylabel("P1 win rate (95% CI)", fontsize=11)
        ax.set_title(f"Same-Model Balance — {mode.capitalize()}\n(P1 = first-move player)",
                     fontsize=12, fontweight='bold')
        ax.legend(fontsize=10)
        ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    fpath = f"{OUT_DIR}/fig5_same_model_balance.pdf"
    plt.savefig(fpath, bbox_inches='tight', dpi=150)
    plt.savefig(fpath.replace('.pdf', '.png'), bbox_inches='tight', dpi=150)
    plt.close()
    print(f"Saved {fpath}")


# ═══════════════════════════════════════════════════════════════════════════════
# Figure 6: Objective completion rate by tier (Preparación / Construcción / Experto)
# ═══════════════════════════════════════════════════════════════════════════════
def fig_objective_breakdown(rows):
    """Score breakdown by circuit type (series/parallel/mixed) per model."""
    # p1_pts_series, p1_pts_parallel, p1_pts_mixed, p1_pts_bridge, p1_pts_cap
    score_types = ["series", "parallel", "mixed"]
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    for ax, mode in zip(axes, ["resistance", "capacitance"]):
        model_data = {m: {t: [] for t in score_types} for m in MODEL_ORDER}

        for r in rows:
            if r["mode"] != mode:
                continue
            for pid in ("p1", "p2"):
                m = r[f"{pid}_model"]
                if m not in model_data:
                    continue
                for t in score_types:
                    val = to_int(r.get(f"{pid}_pts_{t}", 0))
                    if val > 0:
                        model_data[m][t].append(val)

        x = np.arange(len(MODEL_ORDER))
        width = 0.22
        offsets = [-width, 0, width]
        type_colors = {"series": "#4393c3", "parallel": "#f4a582", "mixed": "#92c47d"}

        for i, t in enumerate(score_types):
            means = [np.mean(model_data[m][t]) if model_data[m][t] else 0
                     for m in MODEL_ORDER]
            bars = ax.bar(x + offsets[i], means, width,
                          label=t.capitalize(),
                          color=type_colors[t], alpha=0.85)

        ax.set_xticks(x)
        ax.set_xticklabels([MODEL_SHORT[m] for m in MODEL_ORDER], fontsize=11)
        ax.set_ylabel("Avg points per completed objective", fontsize=10)
        ax.set_title(f"Score by Circuit Type — {mode.capitalize()}",
                     fontsize=12, fontweight='bold')
        ax.legend(fontsize=10)
        ax.grid(axis='y', alpha=0.3)
        ax.set_ylim(bottom=0)

    plt.tight_layout()
    fpath = f"{OUT_DIR}/fig6_objective_breakdown.pdf"
    plt.savefig(fpath, bbox_inches='tight', dpi=150)
    plt.savefig(fpath.replace('.pdf', '.png'), bbox_inches='tight', dpi=150)
    plt.close()
    print(f"Saved {fpath}")


# ═══════════════════════════════════════════════════════════════════════════════
# Table: Summary statistics for paper
# ═══════════════════════════════════════════════════════════════════════════════
def print_summary_table(rows):
    print("\n" + "="*80)
    print("SUMMARY TABLE")
    print("="*80)

    # Cross-model: head-to-head win rates
    print("\n--- Cross-model head-to-head ---")
    pairs = [
        ("llama3.3:70b", "qwen3:32b"),
        ("llama3.3:70b", "mixtral:latest"),
        ("qwen3:32b",    "mixtral:latest"),
    ]
    for m1, m2 in pairs:
        for mode in ["resistance", "capacitance"]:
            p1w = p2w = draws = 0
            for r in rows:
                if r["kind"] != "cross" or r["mode"] != mode:
                    continue
                if r["p1_model"] != m1 or r["p2_model"] != m2:
                    continue
                if r["winner"] == "P1":
                    p1w += 1
                elif r["winner"] == "P2":
                    p2w += 1
                else:
                    draws += 1
            n = p1w + p2w + draws
            c, lo, hi = wilson_ci(p1w, n)
            print(f"  {MODEL_SHORT[m1]:7} vs {MODEL_SHORT[m2]:7} {mode:12}: "
                  f"P1 wins {p1w:3}/{n} = {c:.0%} [95%CI {lo:.0%}–{hi:.0%}]  "
                  f"(P2={p2w}, draws={draws})")

    # Same-model: score stats
    print("\n--- Same-model score statistics ---")
    for mode in ["resistance", "capacitance"]:
        print(f"  Mode: {mode}")
        for m in MODEL_ORDER:
            scores = []
            for r in rows:
                if r["kind"] != "same" or r["mode"] != mode or r["p1_model"] != m:
                    continue
                scores += [to_int(r["p1_score"]), to_int(r["p2_score"])]
            if scores:
                print(f"    {MODEL_SHORT[m]:8}: mean={np.mean(scores):.1f} "
                      f"std={np.std(scores):.1f} "
                      f"median={np.median(scores):.0f} "
                      f"[{min(scores)}–{max(scores)}]  n={len(scores)}")

    # LLM call statistics (from trace JSONL files)
    print("\n--- LLM call statistics (same-model games, from trace JSONL) ---")
    for m in MODEL_ORDER:
        s = TRACE_STATS[m]
        n = s["calls"]
        print(f"  {MODEL_SHORT[m]:8}: calls={n}  "
              f"success={s['success']/n:.1%}  fallback={s['fallback']/n:.1%}  "
              f"avg_latency={s['avg_ms']}ms")

    print()


# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    np.random.seed(42)
    rows = load_all()
    total = len(rows)
    same_count = sum(1 for r in rows if r["kind"] == "same")
    cross_count = sum(1 for r in rows if r["kind"] == "cross")
    print(f"Loaded {total} games: {same_count} same-model, {cross_count} cross-model")

    print_summary_table(rows)

    print("Generating figures...")
    fig_winrate_matrix(rows)
    fig_score_distributions(rows)
    fig_reliability(rows)
    fig_model_ranking(rows)
    fig_same_model_balance(rows)
    fig_objective_breakdown(rows)

    print(f"\nAll figures saved to {OUT_DIR}/")
