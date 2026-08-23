import random
import os
import json
import re
import copy
import time
from breadboard_game import ResistorCard, WireCard, PlacedComp
from openai import OpenAI

class HeuristicAgent:
    """Deterministic, objective-driven agent for v9.0 final rules.
    Picks one objective, computes exact circuit plan, places step by step."""

    def __init__(self, name="Heuristic", player_idx=0):
        self.name, self.player_idx = name, player_idx
        if player_idx == 0:
            self.circuit_cols = list(range(2, 7))        # A→E (left to right)
        else:
            self.circuit_cols = list(range(11, 6, -1))   # J→F (right to left)
        self._current_plan = None      # locked circuit plan [(col_idx, row_idx, value), ...]
        self._plan_start_row = None    # the row where the plan begins

    def _next_start_row(self, game, pid):
        """First available row for a new circuit — past all existing components with a 1-row gap."""
        my_comps = [c for c in game.placed_components if c.owner == pid and c.value > 0]
        if not my_comps:
            return 0
        max_row = max(max(c.r1, c.r2) for c in my_comps)
        next_r = max_row + 2  # skip one empty row as separator
        return next_r if next_r <= 13 else None  # need next_r and next_r+1 within rows 0-14

    def _get_circuit_plan(self, obj, hand_vals):
        """Return an ordered list of (col_idx, row_idx, value) for the objective,
        or None if the hand cannot satisfy it.
        col_idx: index into self.circuit_cols; row_idx: offset from start_row."""
        from itertools import combinations, permutations
        target = obj.target_req
        n = obj.component_count
        route = obj.route_desc
        tol = 0.051
        is_cap = getattr(obj, "objective_type", "resistance") == "capacitance"

        def close(v, t): return abs(v - t) / max(t, 1) <= tol

        def parallel_eq(vals):
            # Resistors: 1/sum(1/v);  Capacitors: sum(v)
            if is_cap:
                return sum(vals)
            cond = sum(1.0 / v for v in vals if v > 0)
            return 1.0 / cond if cond > 0 else float('inf')

        def series_eq(vals):
            # Resistors: sum(v);  Capacitors: 1/sum(1/v)
            if is_cap:
                cond = sum(1.0 / v for v in vals if v > 0)
                return 1.0 / cond if cond > 0 else float('inf')
            return sum(vals)

        if 'Parallel' in route and 'Mixed' not in route:
            # All in same 2-row span, different columns
            for combo in combinations(range(len(hand_vals)), n):
                vals = [hand_vals[i] for i in combo]
                if close(parallel_eq(vals), target):
                    return [(ci, 0, vals[ci]) for ci in range(n)]

        elif 'Series' in route and 'Mixed' not in route:
            # All in same column, consecutive rows
            for combo in combinations(range(len(hand_vals)), n):
                for perm in permutations([hand_vals[i] for i in combo]):
                    if close(series_eq(list(perm)), target):
                        return [(0, ri, perm[ri]) for ri in range(n)]

        elif 'Mixed' in route or 'Bridge' in route:
            for combo in combinations(range(len(hand_vals)), n):
                vals_c = [hand_vals[i] for i in combo]
                for perm in permutations(vals_c):
                    if n == 3:
                        # series_top + parallel_bottom: perm[0] series, perm[1]||perm[2] parallel
                        par_val = parallel_eq(list(perm[1:]))
                        if close(series_eq([perm[0], par_val]), target):
                            return [(0, 0, perm[0]), (0, 1, perm[1]), (1, 1, perm[2])]
                        # parallel_top + series_bottom
                        par_val2 = parallel_eq(list(perm[:2]))
                        if close(series_eq([par_val2, perm[2]]), target):
                            return [(0, 0, perm[0]), (1, 0, perm[1]), (0, 1, perm[2])]
                    elif n == 4:
                        # Simpler: try all splits in two sub-groups stacked
                        for s in range(1, 4):
                            top = list(perm[:s])
                            bot = list(perm[s:])
                            top_val = parallel_eq(top)
                            bot_val = parallel_eq(bot)
                            if close(series_eq([top_val, bot_val]), target):
                                plan = []
                                for ci, v in enumerate(top):
                                    plan.append((ci, 0, v))
                                for ci, v in enumerate(bot):
                                    plan.append((ci, len(top), v))
                                return plan

        return None

    def _pick_objective(self, game, pid, inv, objectives):
        """Pick the objective most achievable with the current hand."""
        hand_vals = [c.value for c in inv if c.value > 0]
        for obj in objectives:
            if self._get_circuit_plan(obj, hand_vals) is not None:
                return obj
        return objectives[0] if objectives else None

    def get_action(self, game, state):
        pid = self.player_idx
        inv = game.inventories[pid]
        objectives = game.objectives[pid]
        ap = game.actions_remaining

        if ap <= 0:
            return ('pass',)

        placed = game.placed_components
        my_comps = [c for c in placed if c.owner == pid and c.value > 0]

        # Phase 1: complete if any objective matched
        if game.validate_move(state, ('complete',)):
            completed = game.check_objectives(pid)
            if completed:
                self._current_plan = None  # board will be cleared; re-plan next turn
                return ('complete',)

        component_indices = [i for i, c in enumerate(inv) if c.value > 0]
        if not component_indices or not objectives:
            if game.validate_move(state, ('draw',)):
                return ('draw',)
            return ('pass',)

        # Phase 2: lock in a plan when no plan exists.
        # Never re-plan mid-circuit — doing so causes inconsistent placements.
        if self._current_plan is None:
            start_r = self._next_start_row(game, pid)
            if start_r is None:  # zone exhausted
                return ('pass',)
            target_obj = self._pick_objective(game, pid, inv, objectives)
            if target_obj:
                hand_vals = [c.value for c in inv if c.value > 0]
                plan = self._get_circuit_plan(target_obj, hand_vals)
                if plan:
                    self._current_plan = plan
                    self._plan_start_row = start_r
            if self._current_plan is None:
                if game.validate_move(state, ('draw',)):
                    return ('draw',)
                return ('pass',)

        # Phase 3: execute the next unplaced step of the locked plan
        for col_idx, row_idx, value in self._current_plan:
            if col_idx >= len(self.circuit_cols):
                continue
            col = self.circuit_cols[col_idx]
            r = self._plan_start_row + row_idx
            if r < 0 or r + 1 > 14:
                continue
            n1, n2 = r * 14 + col, (r + 1) * 14 + col
            slot = tuple(sorted((n1, n2)))
            if slot in game.slot_occupancy:
                continue  # already placed — advance to next step
            # Find the needed component in hand
            idx = next((i for i, c in enumerate(inv) if c.value == value), None)
            if idx is None:
                # Don't have this component yet — draw to get it
                if game.validate_move(state, ('draw',)):
                    return ('draw',)
                return ('pass',)
            if game.validate_move(state, ('place', idx, n1, n2)):
                return ('place', idx, n1, n2)

        # All plan steps placed — draw if no action left, else pass
        if game.validate_move(state, ('draw',)):
            return ('draw',)
        return ('pass',)

class LLMBaseAgent:
    def __init__(self, name="LLMAgent", player_idx=0, retries=3, model="llama3.3:70b"):
        self.name, self.player_idx, self.retries, self.model = name, player_idx, retries, model
        self.fallback_count = 0
        self._api_attempts = 0
        self._api_ok = 0
        self._current_r0 = 0  # only advances on complete, not per-placement
        self.heuristic_fallback = HeuristicAgent(name=name+"-Fallback", player_idx=player_idx)
        ollama_url = os.environ.get("OLLAMA_URL", "http://localhost:11434/v1")
        self.client = OpenAI(base_url=ollama_url, api_key="ollama")

    def serialize_state(self, game, pid, state, error_hint=None):
        inv, objectives, ap = game.inventories[pid], game.objectives[pid], game.actions_remaining

        # r0 is pinned for the duration of a circuit; only advances when complete is called.
        # Reset for new game (no placed components = fresh board).
        my_comps = [c for c in game.placed_components if c.owner == pid and c.value > 0]
        if not my_comps:
            self._current_r0 = 0
        r0 = self._current_r0

        # Templates anchored at row 0; all n1/n2 shifted by r0*14 at render time.
        # Format: (base_n1, base_n2, label_str, value)
        # base nodes use col 2 (A) or col 3 (B), etc., at rows 0/1/2/3
        templates = {
            # parallel: 2 rows (r0, r0+1), different columns
            (33.33, ""):       ("3-Parallel 33Ω (100‖100‖100)",
                [("R1(100Ω)", 2,  16, 100), ("R2(100Ω)", 3,  17, 100), ("R3(100Ω)", 4, 18, 100)]),
            (50,    ""):       ("Parallel 50Ω (100‖100)",
                [("R1(100Ω)", 2,  16, 100), ("R2(100Ω)", 3,  17, 100)]),
            (66.67, ""):       ("Parallel 67Ω (100‖200)",
                [("R1(100Ω)", 2,  16, 100), ("R2(200Ω)", 3,  17, 200)]),
            (75,    ""):       ("Parallel 75Ω (100‖300)",
                [("R1(100Ω)", 2,  16, 100), ("R2(300Ω)", 3,  17, 300)]),
            (120,   ""):       ("Parallel 120Ω (200‖300)",
                [("R1(200Ω)", 2,  16, 200), ("R2(300Ω)", 3,  17, 300)]),
            # series: 3 rows (r0, r0+1, r0+2), same column A
            (200,   ""):       ("Series 200Ω (100+100)",
                [("R1(100Ω)", 2,  16, 100), ("R2(100Ω)", 16, 30,  100)]),
            (300,   ""):       ("Series 300Ω (100+200)",
                [("R1(100Ω)", 2,  16, 100), ("R2(200Ω)", 16, 30,  200)]),
            (400,   ""):       ("Series 400Ω (100+300)",
                [("R1(100Ω)", 2,  16, 100), ("R2(300Ω)", 16, 30,  300)]),
            (500,   ""):       ("Series 500Ω (200+300)",
                [("R1(200Ω)", 2,  16, 200), ("R2(300Ω)", 16, 30,  300)]),
            # bridge: 4 rows, 2 columns
            (100, "Bridge"):   ("Bridge 100Ω ((100‖100)+(100‖100))",
                [("R1(100Ω)", 2, 16, 100), ("R2(100Ω)", 3, 17, 100),
                 ("R3(100Ω)", 16, 30, 100), ("R4(100Ω)", 17, 31, 100)]),
            # mixed: series on top, parallel on bottom (or vice versa)
            (133.33, "Mixed"): ("Mixed 133Ω (100+(100‖100‖100))",
                [("R1(100Ω series)", 16, 30, 100),
                 ("R2(100Ω parallel)", 3, 17, 100), ("R3(100Ω parallel)", 4, 18, 100),
                 ("R4(100Ω parallel)", 5, 19, 100)]),
            (166.67, "Mixed"): ("Mixed 167Ω (100+(100‖200))",
                [("R1(100Ω series)", 16, 30, 100),
                 ("R2(100Ω parallel)", 2, 16, 100), ("R3(200Ω parallel)", 3, 17, 200)]),
            (175,  "Mixed"):   ("Mixed 175Ω (100+(100‖300))",
                [("R1(100Ω series)", 16, 30, 100),
                 ("R2(100Ω parallel)", 2, 16, 100), ("R3(300Ω parallel)", 3, 17, 300)]),
            (220,  "Mixed"):   ("Mixed 220Ω (100+(200‖300))",
                [("R1(100Ω series)", 16, 30, 100),
                 ("R2(200Ω parallel)", 2, 16, 200), ("R3(300Ω parallel)", 3, 17, 300)]),
            (250,  "Mixed"):   ("Mixed 250Ω (200+(100‖100))",
                [("R1(100Ω parallel)", 2, 16, 100), ("R2(100Ω parallel)", 3, 17, 100),
                 ("R3(200Ω series)", 16, 30, 200)]),
            (350,  "Mixed"):   ("Mixed 350Ω (300+(100‖100))",
                [("R1(100Ω parallel)", 2, 16, 100), ("R2(100Ω parallel)", 3, 17, 100),
                 ("R3(300Ω series)", 16, 30, 300)]),
            # capacitor templates
            (5,    "C"):  ("Series 5µF (10+10)",   [("C1(10µF)", 2, 16, 10), ("C2(10µF)", 16, 30, 10)]),
            (6.67, "C"):  ("Series 6.7µF (10+20)", [("C1(10µF)", 2, 16, 10), ("C2(20µF)", 16, 30, 20)]),
            (7.5,  "C"):  ("Series 7.5µF (10+30)", [("C1(10µF)", 2, 16, 10), ("C2(30µF)", 16, 30, 30)]),
            (12,   "C"):  ("Series 12µF (20+30)",  [("C1(20µF)", 2, 16, 20), ("C2(30µF)", 16, 30, 30)]),
            (3.33, "C"):  ("Series 3.3µF (10+10+10)",
                [("C1(10µF)", 2, 16, 10), ("C2(10µF)", 16, 30, 10), ("C3(10µF)", 30, 44, 10)]),
            (2.5,  "C"):  ("Series 2.5µF (10+10+10+10)",
                [("C1(10µF)", 2, 16, 10), ("C2(10µF)", 16, 30, 10),
                 ("C3(10µF)", 30, 44, 10), ("C4(10µF)", 44, 58, 10)]),
            (40,   "C"):  ("Parallel 40µF (10‖30)", [("C1(10µF)", 2, 16, 10), ("C2(30µF)", 3, 17, 30)]),
            (50,   "C"):  ("Parallel 50µF (20‖30)", [("C1(20µF)", 2, 16, 20), ("C2(30µF)", 3, 17, 30)]),
        }

        key = None
        for o in objectives:
            tag = ""
            if 'Bridge' in getattr(o, 'route_desc', ''): tag = "Bridge"
            elif 'Mixed' in getattr(o, 'route_desc', ''): tag = "Mixed"
            if getattr(o, 'objective_type', 'resistance') == 'capacitance':
                tag = "C" + tag
            key = (o.target_req, tag)
            break

        obj0 = objectives[0]
        target_str = f"{obj0.target_req}{'µF' if getattr(obj0,'objective_type','resistance')=='capacitance' else 'Ω'}"
        scored = len(game.completed_objectives[pid])
        hand_str = ", ".join(f"[{i}]={int(c.value)}Ω" for i, c in enumerate(inv))
        res_idxs = [i for i, c in enumerate(inv) if c.value > 0]
        comp_desc = ', '.join(f'[{i}]={int(inv[i].value)}Ω' for i in res_idxs)

        prompt = f"""CIRCUIT BUILDER — Player P{pid} | Score: {game.scores[pid]} (you) vs {game.scores[1-pid]} (opponent) | {ap} AP left this turn | Objectives scored: {scored}
Goal: score as many objectives as possible. After each complete, IMMEDIATELY start the next circuit at fresh rows.
Node = row*14+col. Place resistors VERTICALLY (same col, adjacent rows). P{pid} zone: cols {'A-E (2-6)' if pid==0 else 'F-J (7-11)'}.
Deck: {len(game.component_deck)} cards left.

HAND: {hand_str}
TARGET: {target_str} ({obj0.route_desc})
Next circuit starts at row {r0} (first free row above your existing components).
"""

        if key in templates:
            title, steps = templates[key]
            prompt += f"CIRCUIT: {title}\n"
            prompt += "Remaining steps:\n"

            remaining = []
            for (label, bn1, bn2, val) in steps:
                n1 = bn1 + r0 * 14
                n2 = bn2 + r0 * 14
                slot = tuple(sorted((n1, n2)))
                if slot not in game.slot_occupancy:
                    r1, c1 = n1 // 14, n1 % 14
                    r2, c2 = n2 // 14, n2 % 14
                    col_lbl = 'ABCDEFGHIJ'[c1 - 2] if 2 <= c1 <= 11 else str(c1)
                    remaining.append((label, n1, n2, val, col_lbl, r1, r2))

            if remaining:
                for (label, n1, n2, val, col_lbl, r1, r2) in remaining:
                    prompt += f"  {label}: {col_lbl}[r{r1}]→{col_lbl}[r{r2}], n1={n1}, n2={n2}\n"
                next_label, next_n1, next_n2, next_val, *_ = remaining[0]
                needed_idxs = [i for i in res_idxs if int(inv[i].value) == next_val]
                prompt += f"\nHAND: {comp_desc}\n"
                if needed_idxs:
                    prompt += f"ACTION: Place {next_label} at n1={next_n1}, n2={next_n2}. inv_idx MUST be one of {needed_idxs}. DO NOT DRAW.\n"
                else:
                    prompt += f"ACTION: Need {next_val}Ω (not in hand) — draw exactly 1 card, then place.\n"
            else:
                prompt += "  (all placed — circuit ready)\n"
                prompt += f"\nHAND: {comp_desc}\n"
                prompt += "ACTION: Use complete to score this circuit NOW. Then immediately start the next one.\n"
        else:
            prompt += f"\nHAND: {comp_desc}\n"
            if res_idxs:
                prompt += f"ACTION: Place a resistor. inv_idx MUST be one of {res_idxs}.\n"
            else:
                prompt += "ACTION: Hand empty — draw a card.\n"
        
        prompt += 'JSON: {"command":"place","inv_idx":<int>,"n1":<int>,"n2":<int>} or {"command":"draw"} or {"command":"complete"}\n'
        
        if error_hint:
            prompt += f"\nLAST MOVE ERROR: {error_hint}\n"
        
        return prompt

    def get_action(self, game, state):
        pid = game.current_player_idx
        if not game.inventories[pid]:
            return ('pass',)
        error_hint = None
        for attempt in range(self.retries):
            prompt = self.serialize_state(game, pid, state, error_hint=error_hint)
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a JSON-only assistant. Output ONLY a single valid JSON object with no explanation, reasoning, or extra keys."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"}, temperature=0.1, timeout=120.0,
                    max_tokens=1024
                )
                self._api_attempts += 1
                raw = response.choices[0].message.content
                # Strip <think>...</think> blocks produced by reasoning models (e.g. DeepSeek-R1)
                raw = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL).strip()
                # Try JSON parse; fall back to regex extraction of command fields
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    m = re.search(r'"command"\s*:\s*"(\w+)"', raw)
                    cmd = m.group(1) if m else None
                    data = {"command": cmd}
                    if cmd == "place":
                        for field in ("inv_idx", "n1", "n2"):
                            fm = re.search(rf'"{field}"\s*:\s*(\d+)', raw)
                            data[field] = int(fm.group(1)) if fm else -1
                # Unwrap nested command (e.g. phi4 returns {"thoughts":..., "command": {...}})
                if isinstance(data.get("command"), dict):
                    data = data["command"]
                cmd = data.get("command")
                if cmd == "place":
                    inv_idx = int(data.get("inv_idx", -1))
                    n1 = int(data.get("n1", -1)); n2 = int(data.get("n2", -1))
                    if not game.validate_move(state, ("place", inv_idx, n1, n2)):
                        inv = game.inventories[pid]
                        w = [i for i,c in enumerate(inv) if c.value == 0]
                        r = [i for i,c in enumerate(inv) if c.value > 0]
                        error_hint = f"Invalid placement idx={inv_idx}. Valid — wires:{w} resistors:{r}"
                        continue
                    self._api_ok += 1
                    return ("place", inv_idx, n1, n2)
                if cmd == "draw":
                    if game.validate_move(state, ("draw",)):
                        self._api_ok += 1
                        return ("draw",)
                    error_hint = "Draw invalid (deck empty?)"
                    continue
                if cmd == "complete":
                    if game.validate_move(state, ("complete",)):
                        self._api_ok += 1
                        # Advance r0 past current components so next circuit gets fresh rows
                        pid2 = game.current_player_idx
                        existing = [c for c in game.placed_components if c.owner == pid2 and c.value > 0]
                        if existing:
                            max_row = max(max(c.r1, c.r2) for c in existing)
                            self._current_r0 = min(max_row + 2, 12)
                        return ("complete",)
                    error_hint = "Complete invalid (no components placed?)"
                    continue
            except Exception as _e:
                self._api_attempts += 1
                print(f"  [LLM] attempt {attempt} failed: {type(_e).__name__}: {_e}")
                error_hint = "JSON error — use valid JSON"
        self.fallback_count += 1
        return self.heuristic_fallback.get_action(game, state)

class OllamaAgent(LLMBaseAgent): pass


class HybridAgent:
    """LLM strategic layer (once per turn) + HeuristicAgent for all placements.

    The LLM decides which objective to pursue and how many cards to draft.
    The heuristic then executes every individual placement action, restricted
    to that single chosen objective so its zone/rail logic targets correctly.
    """

    def __init__(self, name="Hybrid", player_idx=0,
                 base_url=None, model="llama3.3:70b"):
        self.name = name
        self.player_idx = player_idx
        self.model = model

        # Local Ollama only — this is what produced the released self-play corpus.
        self.client = OpenAI(
            base_url=base_url or "http://localhost:11434/v1",
            api_key="ollama",
        )

        self.heuristic = HeuristicAgent(name=f"{name}_heuristic", player_idx=player_idx)

        # Per-turn state
        self._last_turn = -1
        self._focus: object = None   # CircuitCard chosen by LLM
        self._drafts_left = 0        # drafts the LLM requested this turn

        # Stats
        self.llm_calls = 0
        self.llm_ok = 0
        self.fallback_count = 0

        # Trace buffer — flushed by run_pvp.py after each get_action call
        self._pending_traces = []

    def flush_traces(self):
        """Return and clear any LLM trace events generated since the last call."""
        traces = self._pending_traces
        self._pending_traces = []
        return traces

    # ── Public interface ──────────────────────────────────────────────────

    def get_action(self, game, state):
        pid = self.player_idx
        turn = state.get("turn_count", 1)

        # Re-query LLM only when truly needed:
        #   • new turn AND focus objective is already done/gone, OR
        #   • no focus has ever been set
        focus_still_active = self._focus is not None and self._focus in game.objectives[pid]
        new_turn = (turn != self._last_turn)

        if new_turn:
            self._last_turn = turn
            if not focus_still_active:
                # Current objective completed or no focus yet — ask LLM for new strategy
                self._focus, self._drafts_left = self._query_strategy(game, state)
            else:
                # Mid-objective: carry focus forward, don't burn an LLM call
                self._drafts_left = 0

        # If LLM requested draws and we still have some left this turn, draw first
        if self._drafts_left > 0 and game.actions_remaining > 0:
            if game.validate_move(state, ("draw",)):
                self._drafts_left -= 1
                return ("draw",)
            self._drafts_left = 0  # can't draw, stop trying

        # Run heuristic with only the focus objective visible
        return self._heuristic_with_focus(game, state)

    # ── Strategy query ────────────────────────────────────────────────────

    def _query_strategy(self, game, state):
        """Ask the LLM which objective to focus on and how many cards to draft.
        Returns (focus_objective, draft_count). Falls back to heuristic choice on failure."""
        pid = self.player_idx
        objectives = game.objectives[pid]
        if not objectives:
            return None, 0

        # Detect module (resistance vs capacitance)
        is_cap = getattr(objectives[0], "objective_type", "resistance") == "capacitance"
        unit = "µF" if is_cap else "Ω"
        comp_type = "capacitor" if is_cap else "resistor"

        turn = state.get("turn_count", 1)
        my_turn = (turn + 1 - pid) // 2
        turns_left = 6 - max(0, my_turn - 1)
        scores = game.scores if hasattr(game, "scores") else [0, 0]
        inv = game.inventories[pid]

        # Hand with correct units
        r_vals = sorted(c.value for c in inv if c.value > 0)
        hand_desc = f"{[str(int(v)) + unit for v in r_vals]}" if r_vals else "empty hand"

        # Objectives with correct units
        obj_lines = []
        for o in objectives:
            n_comp = getattr(o, "component_count", getattr(o, "n_components", "?"))
            obj_lines.append(
                f'  "{o.route_desc}": target={o.target_req}{unit}, points={o.points}, '
                f'components_needed={n_comp}'
            )
        obj_text = "\n".join(obj_lines)

        # Board state with correct component type
        my_placed = [c for c in game.placed_components if c.owner == pid]
        placed_wires = sum(1 for c in my_placed if c.value == 0)
        placed_vals  = sorted(int(c.value) for c in my_placed if c.value > 0)
        placed_str   = f"{[str(v) + unit for v in placed_vals]}" if placed_vals else f"none"
        board_desc   = f"{placed_wires} wire(s) placed, {comp_type}s on board: {placed_str}"

        # Formula block — explicit rules + examples + deck constraints
        if is_cap:
            formula_block = (
                f"MODULE: Capacitance. Card values available: 10{unit}, 20{unit}, 30{unit} ONLY.\n"
                f"CAPACITOR FORMULAS (opposite of resistors):\n"
                f"  Series:   C_eq = 1/(1/C1 + 1/C2)  → result is SMALLER than either\n"
                f"    e.g. 10{unit} series 10{unit} = 5{unit},  10{unit} series 20{unit} = 6.67{unit}\n"
                f"  Parallel: C_eq = C1 + C2            → result is LARGER (just add)\n"
                f"    e.g. 10{unit} parallel 30{unit} = 40{unit},  20{unit} parallel 30{unit} = 50{unit}"
            )
        else:
            formula_block = (
                f"MODULE: Resistance. Card values available: 100{unit}, 200{unit}, 300{unit} ONLY.\n"
                f"RESISTOR FORMULAS:\n"
                f"  Series:   R_eq = R1 + R2            → result is LARGER (just add)\n"
                f"    e.g. 100{unit} + 200{unit} = 300{unit}\n"
                f"  Parallel: R_eq = 1/(1/R1 + 1/R2)  → result is SMALLER\n"
                f"    e.g. 100{unit} || 100{unit} = 50{unit},  200{unit} || 300{unit} = 120{unit}"
            )

        prompt = (
            f"You are the strategic layer for a circuit-building game agent (player {pid}).\n"
            f"Turn {my_turn}/6 ({turns_left} turn(s) left). Score: you={scores[pid]}, opponent={scores[1-pid]}.\n\n"
            f"Your hand: {hand_desc}\n"
            f"Board (your pieces): {board_desc}\n"
            f"Deck remaining: {len(game.component_deck)} cards\n\n"
            f"{formula_block}\n\n"
            f"Your active objectives:\n{obj_text}\n\n"
            f"Rules reminder:\n"
            f"- 3 AP per turn; place/draw/complete each cost 1 AP.\n"
            f"- Place components vertically in your zone (P0=cols A-E, P1=cols F-J), rows 0-14.\n"
            f"- Use 'complete' action once circuit matches objective; engine auto-connects to rails.\n"
            f"- Draw from deck if a needed component is missing from your hand.\n\n"
            f"Verify your math using the formulas above before deciding.\n\n"
            f"Decide:\n"
            f'1. Which objective to focus on this turn (use exact route_desc string as "focus_objective").\n'
            f'2. How many draws to request this turn (0-2; only draw if missing a specific component).\n\n'
            f'Respond with JSON only:\n'
            f'{{"focus_objective": "<route_desc>", "draft_count": 0, "reasoning": "<one sentence>"}}'
        )

        self.llm_calls += 1
        # Qwen3 thinking models need /no_think appended to suppress chain-of-thought
        # and return content in the standard message.content field.
        is_qwen3 = "qwen3" in self.model.lower()
        user_content = prompt + ("\n/no_think" if is_qwen3 else "")

        # Base trace — filled in below
        trace = {
            "player": pid,
            "model": self.model,
            "turn": state.get("turn_count", 1),
            "my_turn": my_turn,
            "turns_left": turns_left,
            "scores": list(game.scores) if hasattr(game, "scores") else [0, 0],
            "hand": [str(int(v)) + unit for v in r_vals],
            "objectives": [
                {"desc": o.route_desc, "target": o.target_req, "points": o.points,
                 "type": getattr(o, "objective_type", "resistance"),
                 "n_components": getattr(o, "component_count", getattr(o, "n_components", None))}
                for o in objectives
            ],
            "board": [str(v) + unit for v in placed_vals],
            "deck_remaining": len(game.component_deck),
            "prompt": prompt,
            "raw_response": None,
            "focus": None,
            "reasoning": None,
            "draft_count": 0,
            "success": False,
            "fallback": False,
            "elapsed_ms": None,
            "error": None,
        }

        import time as _time
        t0 = _time.time()
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": user_content}],
                max_tokens=200,
                temperature=0.3,
                extra_body={"thinking": {"type": "disabled"}},
            )
            trace["elapsed_ms"] = round((_time.time() - t0) * 1000)
            msg = resp.choices[0].message
            raw = (msg.content or "").strip()
            # Fallback: some thinking models put the answer in reasoning_content
            if not raw:
                extras = getattr(msg, "model_extra", {}) or {}
                raw = (extras.get("reasoning_content") or "").strip()
            # Strip markdown fences if present
            raw = re.sub(r"^```[a-z]*\n?", "", raw).rstrip("` \n")
            trace["raw_response"] = raw

            data = json.loads(raw)
            focus_name = data.get("focus_objective", "")
            draft_count = int(data.get("draft_count", 0))
            reasoning = data.get("reasoning", "")
            trace["reasoning"] = reasoning
            trace["draft_count"] = draft_count

            # Match by route_desc
            focus_obj = next((o for o in objectives if o.route_desc == focus_name), None)
            if focus_obj is None:
                # Partial match fallback
                focus_obj = next(
                    (o for o in objectives if focus_name.lower() in o.route_desc.lower()), None
                )

            if focus_obj:
                self.llm_ok += 1
                trace["focus"] = focus_obj.route_desc
                trace["success"] = True
                self._pending_traces.append(trace)
                print(f"  [LLM] focus={focus_obj.route_desc} drafts={draft_count} | {reasoning}")
                return focus_obj, max(0, min(draft_count, 2))

            trace["error"] = f"no_match: '{focus_name}'"
            print(f"  [LLM] no match for '{focus_name}', using default")
        except Exception as e:
            trace["elapsed_ms"] = round((_time.time() - t0) * 1000)
            trace["error"] = str(e)
            print(f"  [LLM] error: {e}")

        self.fallback_count += 1
        trace["fallback"] = True
        best = max(objectives, key=lambda o: o.points)
        trace["focus"] = best.route_desc
        self._pending_traces.append(trace)
        # Default: highest-value completable objective
        return best, 0

    # ── Draft helper ──────────────────────────────────────────────────────

    def _should_draw(self, game, focus_obj):
        """Return True if drawing from deck is worthwhile for focus_obj."""
        if not game.component_deck:
            return False
        pid = self.player_idx
        inv = game.inventories[pid]
        # Draw if hand is small (fewer than 5 components)
        return len([c for c in inv if c.value > 0]) < 5

    # ── Heuristic execution with single-objective focus ───────────────────

    def _heuristic_with_focus(self, game, state):
        pid = self.player_idx
        original_objectives = game.objectives[pid]

        # Temporarily restrict objectives to focus only
        if self._focus and self._focus in original_objectives:
            game.objectives[pid] = [self._focus]

        try:
            action = self.heuristic.get_action(game, state)
        finally:
            game.objectives[pid] = original_objectives

        return action