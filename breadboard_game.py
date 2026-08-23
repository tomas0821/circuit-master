import numpy as np
import random
import copy
from collections import deque
from boardwalk import Game, Board

# --- v9.0 Final Rules (Version Final Manual_de_Circuit_Master.pdf) ---

class ResistorCard:
    def __init__(self, value): self.value = value
    def __repr__(self): return f"{self.value}Ω"

class CapacitorCard:
    def __init__(self, value): self.value = value
    def __repr__(self): return f"{self.value}µF"

class WireCard:
    # Not dealt to players. Used internally for virtual auto-connect wires.
    def __init__(self): self.value = 0
    def __repr__(self): return "Wire"

class CircuitCard:
    def __init__(self, id, target_req, points, route_desc="", position_type=None,
                 objective_type="resistance", component_count=2):
        self.id, self.target_req, self.points, self.route_desc = id, target_req, points, route_desc
        self.position_type = position_type
        self.objective_type = objective_type
        self.component_count = component_count
    def __str__(self):
        unit = "µF" if self.objective_type == "capacitance" else "Ω"
        v_str = f"{self.target_req}{unit}" if self.target_req < 1000 else f"{self.target_req/1000:g}mF"
        return f"[#{self.id}] {v_str} ({self.points} pts) - {self.route_desc}"


class BreadboardGame(Game):
    # P0 = cols 2-6 (A-E), P1 = cols 7-11 (F-J); both share rows 0-14
    ZONES = {0: range(2, 7), 1: range(7, 12)}

    def __init__(self, player_names=["Team-1", "Team-2"], mode='resistance'):
        super().__init__(Board((15, 14)))
        self.player_names = player_names
        self.mode = mode  # 'resistance' or 'capacitance'
        self.current_player_idx = 0
        self.inventories, self.objectives = [[], []], [[], []]
        self.scores, self.completed_objectives = [0, 0], [[], []]
        self.placed_components = []
        self.node_occupancy = {n: 0 for n in range(210)}
        self.slot_occupancy = set()
        self.actions_remaining, self.turn_action_count = 3, 0
        self.player_turns = [0, 0]
        self._cache_val, self._cache_comps, self._cache_used = None, None, []
        self._cache_rails = (False, False)

        self.component_deck = self._create_component_deck()
        self.objective_deck = self._create_objective_deck()
        for i in range(2):
            self._deal_starting_hand(i)
            self._replenish_objectives(i)

    # ── Deck / Hand ───────────────────────────────────────────────────────────

    def _create_component_deck(self):
        """80-card mode-specific deck: 40 low + 20 mid + 20 high."""
        if self.mode == 'capacitance':
            deck = ([CapacitorCard(10)] * 40 +
                    [CapacitorCard(20)] * 20 +
                    [CapacitorCard(30)] * 20)
        else:
            deck = ([ResistorCard(100)] * 40 +
                    [ResistorCard(200)] * 20 +
                    [ResistorCard(300)] * 20)
        random.shuffle(deck)
        return deck

    def _deal_starting_hand(self, pid):
        """9 low + 4 mid + 2 high = 15 cards per player, drawn from deck."""
        if self.mode == 'capacitance':
            counts = [(10, 9), (20, 4), (30, 2)]
        else:
            counts = [(100, 9), (200, 4), (300, 2)]
        hand = []
        for val, n in counts:
            removed = 0
            remaining = []
            for card in self.component_deck:
                if removed < n and card.value == val:
                    hand.append(card); removed += 1
                else:
                    remaining.append(card)
            self.component_deck = remaining
        random.shuffle(hand)
        self.inventories[pid] = hand

    def _create_objective_deck(self):
        """Tiered objective deck: Preparación on top, Experto at bottom."""
        resistance_objs = [
            # Preparación (2-component)
            CircuitCard(0,  200,    30, "Series 200Ω",    "power_circuit", "resistance", 2),
            CircuitCard(1,  50,     30, "Parallel 50Ω",   "power_circuit", "resistance", 2),
            CircuitCard(2,  300,    30, "Series 300Ω",    "power_circuit", "resistance", 2),
            CircuitCard(3,  66.67,  30, "Parallel 67Ω",   "power_circuit", "resistance", 2),
            CircuitCard(4,  400,    35, "Series 400Ω",    "power_circuit", "resistance", 2),
            CircuitCard(5,  75,     30, "Parallel 75Ω",   "power_circuit", "resistance", 2),
            CircuitCard(6,  500,    40, "Series 500Ω",    "power_circuit", "resistance", 2),
            CircuitCard(7,  120,    35, "Parallel 120Ω",  "power_circuit", "resistance", 2),
            # Construcción (3-component)
            CircuitCard(8,  33.33,  40, "3-Parallel 33Ω", "power_circuit", "resistance", 3),
            CircuitCard(9,  250,    45, "Mixed 250Ω",     "power_circuit", "resistance", 3),
            CircuitCard(10, 350,    45, "Mixed 350Ω",     "power_circuit", "resistance", 3),
            CircuitCard(11, 166.67, 45, "Mixed 167Ω",     "power_circuit", "resistance", 3),
            CircuitCard(12, 175,    45, "Mixed 175Ω",     "power_circuit", "resistance", 3),
            CircuitCard(13, 220,    45, "Mixed 220Ω",     "power_circuit", "resistance", 3),
            # Experto (4-component)
            CircuitCard(14, 100,    65, "Bridge 100Ω",    "power_circuit", "resistance", 4),
            CircuitCard(15, 133.33, 65, "Mixed 133Ω",     "power_circuit", "resistance", 4),
        ]
        capacitance_objs = [
            # Preparación (2-component)
            CircuitCard(20, 5,     30, "Series 5µF",      "power_circuit", "capacitance", 2),
            CircuitCard(21, 6.67,  30, "Series 6.7µF",    "power_circuit", "capacitance", 2),
            CircuitCard(22, 7.5,   30, "Series 7.5µF",    "power_circuit", "capacitance", 2),
            CircuitCard(23, 12,    35, "Series 12µF",     "power_circuit", "capacitance", 2),
            CircuitCard(24, 10,    30, "Series 10µF",     "power_circuit", "capacitance", 2),
            CircuitCard(25, 20,    30, "Parallel 20µF",   "power_circuit", "capacitance", 2),
            CircuitCard(26, 40,    35, "Parallel 40µF",   "power_circuit", "capacitance", 2),
            CircuitCard(27, 50,    35, "Parallel 50µF",   "power_circuit", "capacitance", 2),
            # Construcción (3-component)
            CircuitCard(28, 3.33,  35, "Series 3.3µF",    "power_circuit", "capacitance", 3),
            CircuitCard(29, 4,     40, "Series 4µF",      "power_circuit", "capacitance", 3),
            CircuitCard(30, 6,     40, "Series 6µF",      "power_circuit", "capacitance", 3),
            CircuitCard(31, 8,     45, "Mixed 8µF",       "power_circuit", "capacitance", 3),
            CircuitCard(32, 13.33, 45, "Mixed 13.3µF",    "power_circuit", "capacitance", 3),
            CircuitCard(33, 60,    45, "3-Parallel 60µF", "power_circuit", "capacitance", 3),
            # Experto (4-component)
            CircuitCard(34, 2.5,   65, "Series 2.5µF",    "power_circuit", "capacitance", 4),
            CircuitCard(35, 3,     65, "Series 3µF",      "power_circuit", "capacitance", 4),
        ]

        all_objs = resistance_objs if self.mode == 'resistance' else capacitance_objs
        setup  = [o for o in all_objs if o.component_count == 2]
        build  = [o for o in all_objs if o.component_count == 3]
        expert = [o for o in all_objs if o.component_count == 4]
        random.shuffle(setup); random.shuffle(build); random.shuffle(expert)

        # Repeat for enough supply (6 turns, up to 3 active objectives per team)
        pool = []
        for _ in range(6):
            pool.extend(copy.deepcopy(setup) + copy.deepcopy(build) + copy.deepcopy(expert))
        for i, c in enumerate(pool):
            c.id = i
        return pool

    def _replenish_objectives(self, pid):
        """Draw from top of objective deck until player has 3 objectives."""
        while len(self.objectives[pid]) < 3 and self.objective_deck:
            self.objectives[pid].append(self.objective_deck.pop(0))

    # ── Auto-connect (Option 1) ───────────────────────────────────────────────

    def _auto_rail_connections(self, pid, comps=None):
        """Generate virtual wire PlacedComps connecting the player's circuit to rails.
        Called during 'complete' action and objective checking.
        Top extremal row → minus rail; bottom extremal row → plus rail.
        Pass comps to simulate against a hypothetical component list."""
        source = comps if comps is not None else self.placed_components
        my_comps = [c for c in source if c.owner == pid and c.value > 0]
        if not my_comps:
            return []

        all_cols = [c.c1 for c in my_comps] + [c.c2 for c in my_comps]
        non_rail_cols = [col for col in all_cols if col not in (0, 1, 12, 13)]
        if not non_rail_cols:
            return []

        # Choose left or right rail pair based on average component column
        avg_col = sum(non_rail_cols) / len(non_rail_cols)
        use_right = avg_col >= 7
        plus_col   = 12 if use_right else 0
        minus_col  = 13 if use_right else 1
        bridge_col = 11 if use_right else 2  # innermost rail-adjacent column

        all_rows = [c.r1 for c in my_comps] + [c.r2 for c in my_comps]
        top_row = min(all_rows)
        bot_row = max(all_rows)

        wires = []
        # Top row → minus rail
        n1 = top_row * 14 + bridge_col
        n2 = top_row * 14 + minus_col
        wires.append(PlacedComp(0, pid, n1, n2, top_row, bridge_col, top_row, minus_col, card_type='wire'))
        # Bottom row → plus rail
        n1 = bot_row * 14 + bridge_col
        n2 = bot_row * 14 + plus_col
        wires.append(PlacedComp(0, pid, n1, n2, bot_row, bridge_col, bot_row, plus_col, card_type='wire'))
        return wires

    # ── Physics engine ────────────────────────────────────────────────────────

    def calculate_graph_equivalent(self, virtual_components=None):
        comps = virtual_components if virtual_components is not None else self.placed_components
        if virtual_components is None and self._cache_val is not None and self._cache_comps == len(self.placed_components):
            return self._cache_val, self._cache_used, self._cache_rails[0], self._cache_rails[1]

        resistors = [c for c in comps if c.value > 0]
        wires = [c for c in comps if c.value == 0]

        if not resistors:
            return float('inf'), [], False, False

        # ── Wire-only Union-Find (wires + row-rails, NO resistors) ──
        w_parent = {}
        def w_find(x):
            if w_parent[x] != x:
                w_parent[x] = w_find(w_parent[x])
            return w_parent[x]
        def w_union(x, y):
            px, py = w_find(x), w_find(y)
            if px != py:
                w_parent[px] = py

        for r in range(15):
            for c in range(14):
                w_parent[r * 14 + c] = r * 14 + c

        for c in wires:
            w_union(c.n1, c.n2)

        # Row-rails (0Ω connections within each half-row)
        for r in range(15):
            for c in range(2, 6):
                w_union(r * 14 + c, r * 14 + c + 1)
            for c in range(7, 11):
                w_union(r * 14 + c, r * 14 + c + 1)

        # ── Short-circuit detection ──
        plus_roots = set()
        minus_roots = set()
        for r in range(15):
            plus_roots.add(w_find(r * 14 + 0))
            plus_roots.add(w_find(r * 14 + 12))
            minus_roots.add(w_find(r * 14 + 1))
            minus_roots.add(w_find(r * 14 + 13))

        if plus_roots & minus_roots:
            if virtual_components is None:
                self._cache_val = 0.0
                self._cache_comps = len(self.placed_components)
                self._cache_used = resistors
                self._cache_rails = (True, True)
            return 0.0, resistors, True, True

        # ── Graph series-parallel reduction ──
        from collections import defaultdict

        edge_components = defaultdict(list)
        adj = defaultdict(set)

        for c in resistors:
            u = w_find(c.n1)
            v = w_find(c.n2)
            if u == v:
                continue
            key = tuple(sorted((u, v)))
            edge_components[key].append(c)
            adj[u].add(v)
            adj[v].add(u)

        # Rail super-nodes (only those with resistors attached)
        neg_supernodes = set()
        pos_supernodes = set()
        for r in range(15):
            for c in [1, 13]:
                ns = w_find(r * 14 + c)
                if ns in adj:
                    neg_supernodes.add(ns)
            for c in [0, 12]:
                ns = w_find(r * 14 + c)
                if ns in adj:
                    pos_supernodes.add(ns)

        # Find connected neg/pos pair via BFS
        neg_root, pos_root = None, None
        for nr in neg_supernodes:
            for pr in pos_supernodes:
                visited = {nr}
                queue = [nr]
                while queue:
                    node = queue.pop(0)
                    if node == pr:
                        neg_root, pos_root = nr, pr
                        break
                    for nb in adj[node]:
                        if nb not in visited:
                            visited.add(nb)
                            queue.append(nb)
                if neg_root:
                    break
            if neg_root:
                break

        if neg_root is None:
            # Fallback: no rail-connected path — compute using full Union-Find
            fb_parent = {}
            def fb_find(x):
                if fb_parent[x] != x:
                    fb_parent[x] = fb_find(fb_parent[x])
                return fb_parent[x]
            def fb_union(x, y):
                px, py = fb_find(x), fb_find(y)
                if px != py:
                    fb_parent[px] = py

            for r in range(15):
                for c in range(14):
                    fb_parent[r * 14 + c] = r * 14 + c

            for c in comps:
                fb_union(c.n1, c.n2)

            for r in range(15):
                for c in range(2, 6):
                    fb_union(r * 14 + c, r * 14 + c + 1)
                for c in range(7, 11):
                    fb_union(r * 14 + c, r * 14 + c + 1)

            groups = {}
            for c in resistors:
                root = fb_find(c.n1)
                if root not in groups:
                    groups[root] = []
                groups[root].append(c)

            total_conductance = 0.0
            for group in groups.values():
                if len(group) == 1:
                    total_conductance += 1.0 / group[0].value
                elif len(group) == 2:
                    r1, r2 = group[0], group[1]
                    if r1.n1 == r2.n1 or r1.n1 == r2.n2 or r1.n2 == r2.n1 or r1.n2 == r2.n2:
                        group_R = r1.value + r2.value
                    else:
                        group_R = 1.0 / (1.0/r1.value + 1.0/r2.value)
                    total_conductance += 1.0 / group_R
                else:
                    group_R = 0.0
                    endpoints = {}
                    for c in group:
                        endpoints[c.n1] = endpoints.get(c.n1, 0) + 1
                        endpoints[c.n2] = endpoints.get(c.n2, 0) + 1
                    internal_endpoints = sum(1 for cnt in endpoints.values() if cnt == 2)
                    if internal_endpoints == len(group) - 1:
                        for c in group:
                            group_R += c.value
                    else:
                        for c in group:
                            group_R += 1.0 / c.value
                        group_R = 1.0 / group_R
                    total_conductance += 1.0 / group_R

            if total_conductance == 0:
                return float('inf'), [], False, False

            R_equiv = 1.0 / total_conductance
            return R_equiv, resistors, False, False

        # Build reduction graph: node -> {neighbor: (R_equiv, [components])}
        graph = defaultdict(lambda: defaultdict(lambda: (float('inf'), [])))
        for (u, v), edge_comps in edge_components.items():
            old_R, old_comps = graph[u][v]
            if old_R == float('inf'):
                if len(edge_comps) == 1:
                    new_R = edge_comps[0].value
                else:
                    new_R = 1.0 / sum(1.0 / x.value for x in edge_comps)
                graph[u][v] = (new_R, list(edge_comps))
                graph[v][u] = (new_R, list(edge_comps))
            else:
                conductance = 1.0 / old_R + sum(1.0 / x.value for x in edge_comps)
                new_R = 1.0 / conductance
                graph[u][v] = (new_R, old_comps + list(edge_comps))
                graph[v][u] = (new_R, old_comps + list(edge_comps))

        # Iterative reduction: dead-end removal, series merge
        while True:
            changed = False

            for node in list(graph.keys()):
                if node in (neg_root, pos_root):
                    continue
                nb_list = list(graph[node].keys())
                if len(nb_list) == 0:
                    del graph[node]
                    changed = True
                elif len(nb_list) == 1:
                    nb = nb_list[0]
                    del graph[node]
                    del graph[nb][node]
                    changed = True

            for node in list(graph.keys()):
                if node in (neg_root, pos_root):
                    continue
                nb_list = list(graph[node].keys())
                if len(nb_list) != 2:
                    continue
                n1, n2 = nb_list
                R1, comps1 = graph[node][n1]
                R2, comps2 = graph[node][n2]
                R_series = R1 + R2
                comps_new = comps1 + comps2

                del graph[node]
                del graph[n1][node]
                del graph[n2][node]

                if n2 in graph[n1]:
                    old_R, old_comps = graph[n1][n2]
                    R_comb = 1.0 / (1.0 / old_R + 1.0 / R_series)
                    graph[n1][n2] = (R_comb, old_comps + comps_new)
                    graph[n2][n1] = (R_comb, old_comps + comps_new)
                else:
                    graph[n1][n2] = (R_series, comps_new)
                    graph[n2][n1] = (R_series, comps_new)
                changed = True
                break

            if not changed:
                break

        if pos_root not in graph.get(neg_root, {}):
            return float('inf'), [], False, False

        R_equiv, used = graph[neg_root][pos_root]

        used_resistors = []
        seen_ids = set()
        for c in used:
            nid = id(c)
            if nid not in seen_ids:
                seen_ids.add(nid)
                used_resistors.append(c)

        connected_to_plus = True
        connected_to_minus = True

        if virtual_components is None:
            self._cache_val = R_equiv
            self._cache_comps = len(self.placed_components)
            self._cache_used = used_resistors
            self._cache_rails = (connected_to_plus, connected_to_minus)
        return R_equiv, used_resistors, connected_to_plus, connected_to_minus

    def calculate_graph_capacitance(self, virtual_components=None):
        """Compute equivalent capacitance using series-parallel graph reduction.
        Capacitance laws are the mathematical dual of resistance:
        - Series: C_eq = 1/(1/C1 + 1/C2)  (same math as parallel resistors)
        - Parallel: C_eq = C1 + C2        (same math as series resistors)
        """
        comps = virtual_components if virtual_components is not None else self.placed_components
        caps = [c for c in comps if getattr(c, 'card_type', 'resistor') == 'capacitor']
        wires = [c for c in comps if c.value == 0]

        if not caps:
            return float('inf'), [], False, False

        # Wire-only Union-Find (same as resistor version)
        w_parent = {}
        def w_find(x):
            if w_parent[x] != x: w_parent[x] = w_find(w_parent[x])
            return w_parent[x]
        def w_union(x, y):
            px, py = w_find(x), w_find(y)
            if px != py: w_parent[px] = py

        for r in range(15):
            for c in range(14):
                w_parent[r * 14 + c] = r * 14 + c
        for c in wires: w_union(c.n1, c.n2)
        for r in range(15):
            for c in range(2, 6): w_union(r * 14 + c, r * 14 + c + 1)
            for c in range(7, 11): w_union(r * 14 + c, r * 14 + c + 1)

        plus_roots, minus_roots = set(), set()
        for r in range(15):
            plus_roots.add(w_find(r * 14 + 0)); plus_roots.add(w_find(r * 14 + 12))
            minus_roots.add(w_find(r * 14 + 1)); minus_roots.add(w_find(r * 14 + 13))
        if plus_roots & minus_roots: return 0.0, [], True, True

        from collections import defaultdict
        edge_components = defaultdict(list)
        adj = defaultdict(set)
        for cap in caps:
            u, v = w_find(cap.n1), w_find(cap.n2)
            if u != v:
                edge_components[(min(u, v), max(u, v))].append(cap)
                adj[u].add(v); adj[v].add(u)

        # Find a connected (neg, pos) pair via BFS — same logic as resistance engine.
        neg_supernodes = {w_find(r * 14 + c) for r in range(15) for c in (1, 13) if w_find(r * 14 + c) in adj}
        pos_supernodes = {w_find(r * 14 + c) for r in range(15) for c in (0, 12) if w_find(r * 14 + c) in adj}
        neg_root, pos_root = None, None
        for nr in neg_supernodes:
            for pr in pos_supernodes:
                visited, queue = {nr}, [nr]
                while queue:
                    node = queue.pop(0)
                    if node == pr:
                        neg_root, pos_root = nr, pr
                        break
                    for nb in adj[node]:
                        if nb not in visited:
                            visited.add(nb); queue.append(nb)
                if neg_root:
                    break
            if neg_root:
                break
        if neg_root is None:
            neg_root = next(iter(neg_supernodes), w_find(1))
            pos_root = next(iter(pos_supernodes), w_find(12))

        if not edge_components and neg_root != pos_root:
            groups = defaultdict(list)
            for c in caps:
                groups[w_find(c.n1)].append(c)
            total_capacitance = 0.0
            for root, group in groups.items():
                if not group: continue
                if len(group) == 1:
                    total_capacitance += group[0].value
                else:
                    endpoints = {}
                    for c in group:
                        endpoints[c.n1] = endpoints.get(c.n1, 0) + 1
                        endpoints[c.n2] = endpoints.get(c.n2, 0) + 1
                    internal_endpoints = sum(1 for cnt in endpoints.values() if cnt == 2)
                    if internal_endpoints == len(group) - 1:
                        group_C = 0.0
                        for c in group: group_C += 1.0 / c.value
                        group_C = 1.0 / group_C if group_C > 0 else 0
                    else:
                        group_C = sum(c.value for c in group)
                    total_capacitance += group_C
            if total_capacitance == 0: return float('inf'), [], False, False
            return total_capacitance, caps, False, False

        graph = defaultdict(lambda: defaultdict(lambda: (float('inf'), [])))
        for (u, v), edge_comps in edge_components.items():
            old_C, old_comps = graph[u][v]
            if old_C == float('inf'):
                if len(edge_comps) == 1:
                    new_C = edge_comps[0].value
                else:
                    new_C = sum(x.value for x in edge_comps)
                graph[u][v] = (new_C, list(edge_comps))
                graph[v][u] = (new_C, list(edge_comps))
            else:
                new_C = old_C + sum(x.value for x in edge_comps)
                graph[u][v] = (new_C, old_comps + list(edge_comps))
                graph[v][u] = (new_C, old_comps + list(edge_comps))

        while True:
            changed = False
            for node in list(graph.keys()):
                if node in (neg_root, pos_root): continue
                nb_list = list(graph[node].keys())
                if len(nb_list) == 0: del graph[node]; changed = True
                elif len(nb_list) == 1:
                    nb = nb_list[0]; del graph[node]; del graph[nb][node]; changed = True
            for node in list(graph.keys()):
                if node in (neg_root, pos_root): continue
                nb_list = list(graph[node].keys())
                if len(nb_list) != 2: continue
                n1, n2 = nb_list
                C1, comps1 = graph[node][n1]
                C2, comps2 = graph[node][n2]
                C_series = 1.0 / (1.0 / C1 + 1.0 / C2) if C1 > 0 and C2 > 0 else 0
                comps_new = comps1 + comps2
                del graph[node]; del graph[n1][node]; del graph[n2][node]
                if n2 in graph[n1]:
                    old_C, old_comps = graph[n1][n2]
                    C_comb = old_C + C_series
                    graph[n1][n2] = (C_comb, old_comps + comps_new)
                    graph[n2][n1] = (C_comb, old_comps + comps_new)
                else:
                    graph[n1][n2] = (C_series, comps_new)
                    graph[n2][n1] = (C_series, comps_new)
                changed = True; break
            if not changed: break

        if pos_root not in graph.get(neg_root, {}):
            return float('inf'), [], False, False

        C_equiv, used = graph[neg_root][pos_root]
        used_caps = []
        seen_ids = set()
        for c in used:
            if id(c) not in seen_ids: seen_ids.add(id(c)); used_caps.append(c)
        return C_equiv, used_caps, True, True

    # ── Circuit group detection ───────────────────────────────────────────────

    def _identify_circuit_groups(self, components):
        """Partition components into groups that are physically connected on the board.
        Two components are in the same group if they share a row within the same
        breadboard half (left cols 2-6 or right cols 7-11), directly or transitively."""
        if not components:
            return []
        n = len(components)
        parent = list(range(n))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(x, y):
            px, py = find(x), find(y)
            if px != py:
                parent[px] = py

        def half(col):
            return 'left' if col in range(2, 7) else 'right'

        for i in range(n):
            ci = components[i]
            rows_i = {ci.r1, ci.r2}
            hi = half(ci.c1)
            for j in range(i + 1, n):
                cj = components[j]
                if half(cj.c1) == hi and rows_i & {cj.r1, cj.r2}:
                    union(i, j)

        groups = {}
        for i in range(n):
            root = find(i)
            groups.setdefault(root, []).append(components[i])
        return list(groups.values())

    # ── Circuit helpers ───────────────────────────────────────────────────────

    def get_player_circuit_components(self, pid):
        """Return placed components forming pid's active circuit (for highlighting)."""
        auto_wires = self._auto_rail_connections(pid)
        my_resistors = [c for c in self.placed_components
                        if c.owner == pid and c.value > 0
                        and getattr(c, 'card_type', 'resistor') != 'capacitor']
        my_caps = [c for c in self.placed_components
                   if c.owner == pid
                   and getattr(c, 'card_type', 'resistor') == 'capacitor']
        _, used_r, _, _ = self.calculate_graph_equivalent(virtual_components=auto_wires + my_resistors)
        _, used_c, _, _ = self.calculate_graph_capacitance(virtual_components=auto_wires + my_caps)
        return auto_wires + used_r + used_c

    def is_connected_to_rails(self):
        """Check if placed circuit is connected to both + and - power rails."""
        _, _, plus, minus = self.calculate_graph_equivalent()
        return (plus, minus)

    def check_objectives(self, pid):
        """Check objectives for player pid. Each physically separate circuit group
        is auto-connected independently so completed circuits don't interfere with
        in-progress ones. Returns list of matched CircuitCard objectives."""
        my_resistors = [c for c in self.placed_components
                        if c.owner == pid and c.value > 0
                        and getattr(c, 'card_type', 'resistor') != 'capacitor']
        my_capacitors = [c for c in self.placed_components
                         if c.owner == pid
                         and getattr(c, 'card_type', 'resistor') == 'capacitor']

        r_circuits = []
        for group in self._identify_circuit_groups(my_resistors):
            auto_wires = self._auto_rail_connections(pid, comps=group)
            val, used, plus, minus = self.calculate_graph_equivalent(
                virtual_components=auto_wires + group)
            if val != float('inf') and used and plus and minus:
                r_circuits.append((val, used, plus, minus))

        c_circuits = []
        for group in self._identify_circuit_groups(my_capacitors):
            auto_wires = self._auto_rail_connections(pid, comps=group)
            val, used, plus, minus = self.calculate_graph_capacitance(
                virtual_components=auto_wires + group)
            if val != float('inf') and used and plus and minus:
                c_circuits.append((val, used, plus, minus))

        completed = []
        for obj in self.objectives[pid][:]:
            circuits = c_circuits if obj.objective_type == "capacitance" else r_circuits
            for val, used, plus, minus in circuits:
                if not (obj.target_req * 0.95 <= val <= obj.target_req * 1.05):
                    continue
                completed.append(obj)
                break

        return completed

    # ── Move validation & execution ───────────────────────────────────────────

    def validate_move(self, state, action):
        pid = self.current_player_idx
        cmd = action[0]

        if cmd == 'pass':
            return True

        if self.actions_remaining <= 0:
            return False

        if cmd == 'draw':
            return bool(self.component_deck)

        if cmd == 'complete':
            my_comps = [c for c in self.placed_components if c.owner == pid and c.value > 0]
            return bool(my_comps)

        if cmd == 'place':
            if len(action) < 4:
                return False
            _, idx, n1, n2 = action
            if idx >= len(self.inventories[pid]):
                return False
            if not (0 <= n1 < 210 and 0 <= n2 < 210) or n1 == n2:
                return False

            slot = tuple(sorted((n1, n2)))
            if slot in self.slot_occupancy:
                return False

            r1, c1 = n1 // 14, n1 % 14
            r2, c2 = n2 // 14, n2 % 14

            # Row bounds: rows 0-14
            if r1 not in range(15) or r2 not in range(15):
                return False

            # Zone enforcement: component column must be in the player's half
            zone = self.ZONES[pid]
            if c1 not in zone:
                return False

            # Vertical placement: same column, adjacent rows
            if c1 != c2:
                return False
            if abs(r1 - r2) != 1:
                return False

            return True

        return False

    def execute_move(self, state, action):
        pid = self.current_player_idx
        new_state = state.copy()
        new_state['message'] = ""
        cmd = action[0]

        if not self.validate_move(state, action):
            self.actions_remaining = 0
            self._end_turn(new_state)
            return new_state

        self.turn_action_count += 1

        if cmd == 'draw':
            card = self.component_deck.pop(0)
            self.inventories[pid].append(card)
            self.actions_remaining -= 1
            msg = f"Drew {card}."

        elif cmd == 'place':
            _, idx, n1, n2 = action
            card = self.inventories[pid].pop(idx)
            r1, c1 = n1 // 14, n1 % 14
            r2, c2 = n2 // 14, n2 % 14
            ct = "capacitor" if isinstance(card, CapacitorCard) else "resistor"
            comp = PlacedComp(card.value, pid, n1, n2, r1, c1, r2, c2, card_type=ct)
            self.placed_components.append(comp)
            self.board.layout[r1, c1] = comp
            self.board.layout[r2, c2] = comp
            self.slot_occupancy.add(tuple(sorted((n1, n2))))
            self._cache_val = None
            self.actions_remaining -= 1
            msg = f"Placed {card} ({n1}->{n2})."

        elif cmd == 'complete':
            completed = self.check_objectives(pid)
            if completed:
                msg_parts = []
                for obj in completed:
                    self.scores[pid] += obj.points
                    self.objectives[pid].remove(obj)
                    self.completed_objectives[pid].append(obj)
                    msg_parts.append(f"*** Completed {obj} ***")
                msg = " ".join(msg_parts)
            else:
                msg = "Complete attempted — no objective matched."
            self.actions_remaining -= 1

        else:  # pass — free action, ends turn immediately
            self._end_turn(new_state)
            new_state['message'] = "Passed."
            return new_state

        if self.actions_remaining <= 0:
            self._end_turn(new_state)

        new_state['message'] = msg
        return new_state

    def _end_turn(self, state):
        self._replenish_objectives(self.current_player_idx)
        self.player_turns[self.current_player_idx] += 1
        self.actions_remaining = 3
        self.turn_action_count = 0
        self.current_player_idx = 1 - self.current_player_idx
        state['turn_count'] += 1

    # ── Game lifecycle ────────────────────────────────────────────────────────

    def get_initial_state(self):
        self.slot_occupancy.clear()
        self.node_occupancy = {n: 0 for n in range(210)}
        self.placed_components = []
        self._cache_val, self._cache_comps, self._cache_used = None, None, []
        self._cache_rails = (False, False)
        self.inventories = [[], []]
        self.objectives = [[], []]
        self.scores = [0, 0]
        self.completed_objectives = [[], []]
        self.player_turns = [0, 0]
        self.component_deck = self._create_component_deck()
        self.objective_deck = self._create_objective_deck()
        for i in range(2):
            self._deal_starting_hand(i)
            self._replenish_objectives(i)
        self.actions_remaining = 3
        self.turn_action_count = 0
        self.current_player_idx = 0
        return {'turn_count': 1, 'message': "v9.0 Final Rules — ¡Comienza el juego!"}

    def game_finished(self, state):
        # 6 turns per player = 12 half-turns total
        return state['turn_count'] > 12

    def get_final_scores(self):
        """Base points + 10 bonus per completed objective."""
        return [self.scores[i] + 10 * len(self.completed_objectives[i]) for i in range(2)]

    def get_winner_idx(self):
        final = self.get_final_scores()
        if final[0] > final[1]: return 0
        if final[1] > final[0]: return 1
        # Tiebreaker: most components placed
        placed = [sum(1 for c in self.placed_components if c.owner == i) for i in range(2)]
        if placed[0] > placed[1]: return 0
        if placed[1] > placed[0]: return 1
        return None  # Both teams win


class PlacedComp:
    def __init__(self, value, owner, n1, n2, r1, c1, r2, c2, card_type="resistor"):
        self.value, self.owner, self.n1, self.n2 = value, owner, n1, n2
        self.r1, self.c1, self.r2, self.c2, self.locked = r1, c1, r2, c2, False
        self.card_type = card_type  # "resistor", "capacitor", or "wire"
