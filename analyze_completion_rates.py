"""
Card-level and category-level objective completion-rate reconstruction.

The summary CSVs (results/cluster_runs/*.csv) log points earned per category for
resistance only, pooling all capacitance objectives into one field, and cannot
separate how often a category is *attempted* from how often it *succeeds once
attempted*. This script reconstructs a per-objective-card completion rate directly
from the per-turn trace logs (*_trace.jsonl): for each strategy call, it checks
whether the score change on that player's next turn exactly matches the chosen
focus objective's point value, and treats that as evidence the objective was
completed.

This slightly undercounts true completions (a match's final turn per player has
no subsequent turn to check against, so it is excluded from the denominator) but
does not introduce false positives, since an exact point-value match on the
immediately following turn is a specific signal.

Used for PAPER_Circuit_Surge_final.md §4.2/§4.3 (component-count vs. category
difficulty) and §5.3.1 (education cross-check).

Output: printed tables (resistance and capacitance, per-card and per-category).
"""

import json
import glob
import collections

DATA_DIR = "results/cluster_runs"

# Objective card -> (category, n_components), from generate_deck.py CARDS list.
RESISTANCE_CARDS = {
    "Series 200Ω": ("series", 2), "Series 300Ω": ("series", 2),
    "Series 400Ω": ("series", 2), "Series 500Ω": ("series", 2),
    "Parallel 50Ω": ("parallel", 2), "Parallel 67Ω": ("parallel", 2),
    "Parallel 75Ω": ("parallel", 2), "Parallel 120Ω": ("parallel", 2),
    "3-Parallel 33Ω": ("mixed", 3), "Mixed 250Ω": ("mixed", 3), "Mixed 350Ω": ("mixed", 3),
    "Mixed 167Ω": ("mixed", 3), "Mixed 175Ω": ("mixed", 3), "Mixed 220Ω": ("mixed", 3),
    "Bridge 100Ω": ("bridge", 4), "Mixed 133Ω": ("bridge", 4),
}

CAPACITANCE_CARDS = {
    "Series 5µF": ("series", 2), "Series 6.7µF": ("series", 2), "Series 7.5µF": ("series", 2),
    "Series 12µF": ("series", 2), "Series 10µF": ("series", 2),
    "Parallel 20µF": ("parallel", 2), "Parallel 40µF": ("parallel", 2), "Parallel 50µF": ("parallel", 2),
    "Series 3.3µF": ("mixed", 3), "Series 4µF": ("mixed", 3), "Series 6µF": ("mixed", 3),
    "Mixed 8µF": ("mixed", 3), "Mixed 13.3µF": ("mixed", 3), "3-Parallel 60µF": ("mixed", 3),
    "Series 2.5µF": ("bridge", 4), "Series 3µF": ("bridge", 4),
}


def reconstruct(mode, cards):
    files = sorted(glob.glob(f"{DATA_DIR}/*{mode}*_trace.jsonl"))
    focus_attempts = collections.Counter()
    focus_completion = collections.Counter()
    cat_attempts = collections.Counter()
    cat_completion = collections.Counter()

    for fp in files:
        matches = collections.defaultdict(list)
        with open(fp) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                matches[d["match"]].append(d)
        for entries in matches.values():
            entries.sort(key=lambda x: x["turn"])
            for player in (0, 1):
                p_entries = sorted(
                    (e for e in entries if e["player"] == player),
                    key=lambda x: x["turn"],
                )
                for i in range(len(p_entries) - 1):
                    cur, nxt = p_entries[i], p_entries[i + 1]
                    focus = cur.get("focus")
                    if focus not in cards:
                        continue
                    cat, n = cards[focus]
                    focus_attempts[focus] += 1
                    cat_attempts[cat] += 1
                    delta = nxt["scores"][player] - cur["scores"][player]
                    if delta > 0:
                        obj = next(
                            (o for o in cur["objectives"] if o["desc"] == focus), None
                        )
                        if obj and delta == obj["points"]:
                            focus_completion[focus] += 1
                            cat_completion[cat] += 1

    return focus_attempts, focus_completion, cat_attempts, cat_completion


def report(mode, cards):
    focus_attempts, focus_completion, cat_attempts, cat_completion = reconstruct(mode, cards)
    print(f"=== {mode} ===")
    print("Per-category completion rate (once chosen as focus):")
    for cat in ["series", "parallel", "mixed", "bridge"]:
        a = cat_attempts[cat]
        c = cat_completion[cat]
        if a:
            print(f"  {cat:10} attempts={a:5} completions={c:5} rate={c / a:.1%}")
        else:
            print(f"  {cat:10} attempts=0 (never chosen as focus)")
    print("\nPer-card completion rate:")
    for k in sorted(focus_attempts, key=lambda k: cards[k]):
        cat, n = cards[k]
        a, c = focus_attempts[k], focus_completion[k]
        print(f"  [{cat:8} n={n}] {k:16} attempts={a:5} completions={c:5} rate={c / a:.1%}")
    print()


if __name__ == "__main__":
    report("resistance", RESISTANCE_CARDS)
    report("capacitance", CAPACITANCE_CARDS)
