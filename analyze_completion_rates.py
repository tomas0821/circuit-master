"""
Card-level and category-level objective completion-rate reconstruction.

The summary CSVs (results/cluster_runs/*.csv) log points earned per category for
resistance only, pooling all capacitance objectives into one field, and cannot
separate how often a category is *attempted* from how often it *succeeds once
attempted*. This script reconstructs a per-objective-card completion rate directly
from the per-turn trace logs (*_trace.jsonl): for each strategy call, it checks
whether the player's score increased by exactly the chosen focus objective's point
value by the time of the next signal, and treats that as evidence the objective was
completed.

For all but a player's last turn, "the next signal" is that player's next trace
entry. For a player's LAST turn in a match, there is no next trace entry, so this
script falls back to the match's final score for that player (from the summary
CSV) as the next signal. An earlier version of this script did not do this
fallback and silently excluded every player's final turn from both the attempt
and completion counts — which is fine for an "attempted" count (a final-turn pick
is still an attempt) but wrongly conflated "we didn't measure this" with "this
never happened" for any analysis that read the attempt count as exhaustive. That
bug caused a real error in an earlier paper draft (a claim that a 4-component tier
was "never chosen as a target, 0 of 9,618 calls" when it was in fact chosen 10
times — all on final turns, none completed). Fixed here.

That first fix introduced a second, subtler bug, caught by a later cross-model
referee pass: the match's final CSV score includes a +10-per-objective completion
bonus (get_final_scores() in breadboard_game.py, applied once at game end across
every objective the player ever completed), but the trace's per-turn running score
never includes it (self.scores[pid] += obj.points only). Comparing a final-turn
trace score directly against the raw CSV final score was therefore comparing two
scores on different bases whenever the player had completed anything at all that
game — silently undercounting final-turn completions, which matter a lot here
since final turns are the majority of Mixed-tier attempts. Fixed by subtracting
the CSV's own completion-bonus contribution (10 * p{1,2}_complete_scored) back out
before comparing, in _load_final_scores().

Used for PAPER_Circuit_Surge_final.md (component-count vs. category difficulty).

Output: printed tables (resistance and capacitance, per-card and per-category).
"""

import csv
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


COMPLETION_BONUS = 10  # get_final_scores() in breadboard_game.py: +10 per completed objective


def _load_final_scores(csv_path):
    """match -> [p1_score_no_bonus, p2_score_no_bonus]

    The CSV's own p1_score/p2_score are *final* scores — they include a +10 bonus per
    objective the player completed anywhere in the game (get_final_scores() adds
    10 * len(completed_objectives) once, at game end). The per-turn trace's running
    `scores` field never includes this bonus (self.scores[pid] += obj.points only).
    Comparing a trace score directly against the raw CSV final score is therefore an
    apples-to-oranges mismatch whenever the player completed anything, all game long —
    so we strip the bonus back out here using p{1,2}_complete_scored (the CSV's own
    count of real completions, which is exactly get_final_scores()'s bonus multiplier)
    to make the final score comparable to the trace's bonus-free running scores.
    """
    final = {}
    try:
        with open(csv_path) as fh:
            for row in csv.DictReader(fh):
                p1_bonus = COMPLETION_BONUS * int(row["p1_complete_scored"])
                p2_bonus = COMPLETION_BONUS * int(row["p2_complete_scored"])
                final[int(row["match"])] = [
                    float(row["p1_score"]) - p1_bonus,
                    float(row["p2_score"]) - p2_bonus,
                ]
    except FileNotFoundError:
        pass
    return final


def reconstruct(mode, cards):
    files = sorted(glob.glob(f"{DATA_DIR}/*{mode}*_trace.jsonl"))
    focus_attempts = collections.Counter()
    focus_completion = collections.Counter()
    cat_attempts = collections.Counter()
    cat_completion = collections.Counter()
    final_turn_attempts = collections.Counter()

    for fp in files:
        csv_path = fp.replace("_trace.jsonl", ".csv")
        final_scores = _load_final_scores(csv_path)

        matches = collections.defaultdict(list)
        with open(fp) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                matches[d["match"]].append(d)
        for match_id, entries in matches.items():
            entries.sort(key=lambda x: x["turn"])
            for player in (0, 1):
                p_entries = sorted(
                    (e for e in entries if e["player"] == player),
                    key=lambda x: x["turn"],
                )
                for i in range(len(p_entries)):
                    cur = p_entries[i]
                    focus = cur.get("focus")
                    if focus not in cards:
                        continue
                    cat, n = cards[focus]
                    focus_attempts[focus] += 1
                    cat_attempts[cat] += 1

                    is_last = i == len(p_entries) - 1
                    if is_last:
                        final_turn_attempts[cat] += 1
                        if match_id not in final_scores:
                            continue  # no summary CSV row to fall back on; skip completion check
                        next_score = final_scores[match_id][player]
                    else:
                        next_score = p_entries[i + 1]["scores"][player]

                    delta = next_score - cur["scores"][player]
                    if delta > 0:
                        obj = next(
                            (o for o in cur["objectives"] if o["desc"] == focus), None
                        )
                        if obj and delta == obj["points"]:
                            focus_completion[focus] += 1
                            cat_completion[cat] += 1

    return focus_attempts, focus_completion, cat_attempts, cat_completion, final_turn_attempts


def report(mode, cards):
    focus_attempts, focus_completion, cat_attempts, cat_completion, final_turn_attempts = reconstruct(mode, cards)
    print(f"=== {mode} ===")
    print("Per-category completion rate (all attempts, including final-turn ones):")
    for cat in ["series", "parallel", "mixed", "bridge"]:
        a = cat_attempts[cat]
        c = cat_completion[cat]
        ft = final_turn_attempts[cat]
        if a:
            print(f"  {cat:10} attempts={a:5} (of which final-turn={ft:4}) completions={c:5} rate={c / a:.1%}")
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
