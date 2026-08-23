import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import numpy as np
import os

# ── circuit-schematic renderer ────────────────────────────────────────────────

# Maps objective route_desc → nested topology structure
#   ('R', value)  — resistor
#   ('C', value)  — capacitor
#   ('series',   [child, ...])
#   ('parallel', [child, ...])
_TOPOLOGIES = {
    "Series 200Ω":    ('series',   [('R', 100), ('R', 100)]),
    "Parallel 50Ω":   ('parallel', [('R', 100), ('R', 100)]),
    "Series 300Ω":    ('series',   [('R', 100), ('R', 200)]),
    "Parallel 67Ω":   ('parallel', [('R', 100), ('R', 200)]),
    "Series 400Ω":    ('series',   [('R', 100), ('R', 300)]),
    "Parallel 75Ω":   ('parallel', [('R', 100), ('R', 300)]),
    "Series 500Ω":    ('series',   [('R', 200), ('R', 300)]),
    "Parallel 120Ω":  ('parallel', [('R', 200), ('R', 300)]),
    "3-Parallel 33Ω": ('parallel', [('R', 100), ('R', 100), ('R', 100)]),
    "Mixed 250Ω":     ('series',   [('R', 200), ('parallel', [('R', 100), ('R', 100)])]),
    "Mixed 350Ω":     ('series',   [('R', 300), ('parallel', [('R', 100), ('R', 100)])]),
    "Mixed 167Ω":     ('series',   [('R', 100), ('parallel', [('R', 100), ('R', 200)])]),
    "Mixed 175Ω":     ('series',   [('R', 100), ('parallel', [('R', 100), ('R', 300)])]),
    "Mixed 220Ω":     ('series',   [('R', 100), ('parallel', [('R', 200), ('R', 300)])]),
    "Bridge 100Ω":    ('series',   [('parallel', [('R', 100), ('R', 100)]),
                                    ('parallel', [('R', 100), ('R', 100)])]),
    "Mixed 133Ω":     ('series',   [('R', 100), ('parallel', [('R', 100), ('R', 100), ('R', 100)])]),
    "Series 5µF":    ('series',   [('C', 10), ('C', 10)]),
    "Series 6.7µF":  ('series',   [('C', 10), ('C', 20)]),
    "Series 7.5µF":  ('series',   [('C', 10), ('C', 30)]),
    "Series 12µF":   ('series',   [('C', 20), ('C', 30)]),
    "Series 3.3µF":  ('series',   [('C', 10), ('C', 10), ('C', 10)]),
    "Series 2.5µF":   ('series',   [('C', 10), ('C', 10), ('C', 10), ('C', 10)]),
    "Parallel 40µF":  ('parallel', [('C', 10), ('C', 30)]),
    "Parallel 50µF":  ('parallel', [('C', 20), ('C', 30)]),
    # new capacitance objectives
    "Series 10µF":    ('series',   [('C', 20), ('C', 20)]),
    "Parallel 20µF":  ('parallel', [('C', 10), ('C', 10)]),
    "Series 4µF":     ('series',   [('C', 10), ('C', 10), ('C', 20)]),
    "Series 6µF":     ('series',   [('C', 10), ('C', 30), ('C', 30)]),
    "3-Parallel 60µF":('parallel', [('C', 10), ('C', 20), ('C', 30)]),
    "Mixed 8µF":      ('series',   [('C', 10), ('parallel', [('C', 20), ('C', 20)])]),
    "Mixed 13.3µF":   ('series',   [('C', 20), ('parallel', [('C', 20), ('C', 20)])]),
    "Series 3µF":     ('series',   [('C', 10), ('C', 10), ('C', 10), ('C', 30)]),
}


def _max_parallel_branches(topo):
    """Return the maximum number of parallel branches at any level."""
    if topo[0] in ('R', 'C'):
        return 1
    if topo[0] == 'parallel':
        return len(topo[1])
    return max(_max_parallel_branches(c) for c in topo[1])


def _draw_element(ax, topo, x0, x1, yc, yspan, lw=1.8, fsize=7.5, color='k'):
    """Recursively draw a circuit element within [x0,x1] centered at yc."""
    kind = topo[0]

    if kind in ('R', 'C'):
        value, unit = topo[1], ('Ω' if kind == 'R' else 'µF')
        w = x1 - x0
        margin = max(w * 0.18, 0.25)
        bx0, bx1 = x0 + margin, x1 - margin
        bh = min(yspan * 0.30, 1.0)

        ax.plot([x0, bx0], [yc, yc], color=color, lw=lw, solid_capstyle='round', zorder=2)
        ax.plot([bx1, x1], [yc, yc], color=color, lw=lw, solid_capstyle='round', zorder=2)

        if kind == 'R':
            # ANSI zigzag — density adapts to body width (~0.5 units per tooth)
            h = min(yspan * 0.15, 0.65)
            body_w = bx1 - bx0
            n_segs = max(8, int(round(body_w / 0.32)))
            if n_segs % 2 != 0:
                n_segs += 1
            d = body_w / n_segs
            zx = [bx0 + i * d for i in range(n_segs + 1)]
            zy = [yc if (i == 0 or i == n_segs) else (yc + h if i % 2 == 1 else yc - h)
                  for i in range(n_segs + 1)]
            ax.plot(zx, zy, color=color, lw=lw, solid_capstyle='round',
                    solid_joinstyle='round', zorder=3)
            ax.text((bx0 + bx1) / 2, yc - h - 0.15, f"{value}Ω",
                    ha='center', va='top', fontsize=max(fsize - 1, 6), color='#444', zorder=4)
        else:
            # Standard capacitor symbol: two short parallel vertical lines
            mid = (bx0 + bx1) / 2
            gap = max((bx1 - bx0) * 0.08, 0.10)
            cap_h = max(bh * 1.6, 0.65)
            ax.plot([bx0, mid - gap], [yc, yc], color=color, lw=lw, zorder=2)
            ax.plot([mid + gap, bx1], [yc, yc], color=color, lw=lw, zorder=2)
            ax.plot([mid - gap, mid - gap], [yc - cap_h / 2, yc + cap_h / 2],
                    color=color, lw=lw * 2.0, solid_capstyle='butt', zorder=3)
            ax.plot([mid + gap, mid + gap], [yc - cap_h / 2, yc + cap_h / 2],
                    color=color, lw=lw * 2.0, solid_capstyle='butt', zorder=3)
            ax.text(mid, yc - cap_h / 2 - 0.15, f"{value}µF",
                    ha='center', va='top', fontsize=max(fsize - 1, 6), color='#444', zorder=4)

    elif kind == 'series':
        n = len(topo[1])
        dx = (x1 - x0) / n
        for i, child in enumerate(topo[1]):
            _draw_element(ax, child, x0 + i * dx, x0 + (i + 1) * dx,
                          yc, yspan, lw, fsize, color)

    elif kind == 'parallel':
        children = topo[1]
        n = len(children)
        branch_yspan = yspan / n
        spacing = min(branch_yspan * 0.80, 2.0)
        half = (n - 1) / 2.0
        y_centers = [yc + (half - i) * spacing for i in range(n)]

        bx0_bus = x0 + (x1 - x0) * 0.04
        bx1_bus = x1 - (x1 - x0) * 0.04
        y_min, y_max = min(y_centers), max(y_centers)

        # Vertical buses
        ax.plot([bx0_bus, bx0_bus], [y_min, y_max],
                color=color, lw=lw, solid_capstyle='round', zorder=2)
        ax.plot([bx1_bus, bx1_bus], [y_min, y_max],
                color=color, lw=lw, solid_capstyle='round', zorder=2)
        # Horizontal lead-ins at yc
        ax.plot([x0, bx0_bus], [yc, yc], color=color, lw=lw, solid_capstyle='round', zorder=2)
        ax.plot([bx1_bus, x1], [yc, yc], color=color, lw=lw, solid_capstyle='round', zorder=2)

        # Junction dots at every connection point on each bus
        junction_ys = sorted(set(y_centers + [yc]))
        for yj in junction_ys:
            ax.plot(bx0_bus, yj, 'o', color=color, markersize=3.5, zorder=5)
            ax.plot(bx1_bus, yj, 'o', color=color, markersize=3.5, zorder=5)

        for child, yb in zip(children, y_centers):
            _draw_element(ax, child, bx0_bus, bx1_bus,
                          yb, branch_yspan * 0.70, lw, fsize, color)


def _draw_objective_card(ax, obj, player_color='k', completed=False):
    """Draw one objective card with a circuit schematic."""
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis('off')

    unit = "µF" if getattr(obj, 'objective_type', 'resistance') == "capacitance" else "Ω"
    alpha = 0.35 if completed else 1.0

    # blank write-in line (students calculate the value)
    ax.text(1.0, 9.5, "=", ha='left', va='center', fontsize=9, fontweight='bold',
            color=player_color, alpha=alpha * 0.7)
    ax.plot([1.8, 8.2], [9.35, 9.35], color=player_color, lw=1.2, alpha=alpha * 0.6)
    ax.text(8.5, 9.5, unit, ha='left', va='center', fontsize=8, fontweight='bold',
            color=player_color, alpha=alpha * 0.7)
    ax.text(5, 8.5, f"{obj.points} pts", ha='center', va='top', fontsize=7.5,
            color='gray', alpha=alpha)

    topo = _TOPOLOGIES.get(obj.route_desc)
    if topo is None:
        ax.text(5, 4.5, obj.route_desc, ha='center', va='center', fontsize=7,
                color='gray', alpha=alpha)
    else:
        max_n = _max_parallel_branches(topo)
        yspan = min(6.5, max(2.5, max_n * 1.9))
        yc = 4.2
        _draw_element(ax, topo, 0.8, 9.2, yc, yspan, lw=1.6, fsize=7.0,
                      color=('#aaa' if completed else '#222'))

    if completed:
        ax.text(5, 5, '✓', ha='center', va='center', fontsize=32,
                color='#2e7d32', alpha=0.6, zorder=10)

    border_color = '#2e7d32' if completed else player_color
    border = plt.Rectangle((0.2, 0.1), 9.6, 9.6, fill=False,
                            edgecolor=border_color, lw=1.5, alpha=0.5, zorder=1)
    ax.add_patch(border)

# ── end schematic renderer ────────────────────────────────────────────────────


def _describe_circuit(used_resistors):
    """Describe circuit using || for parallel and () for grouping, e.g. (100‖100)+(100‖100)."""
    if not used_resistors:
        return ["No circuit"]
    
    # Build w_find to detect parallel groups via row-rail connections
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
    
    for c in used_resistors:
        if c.value == 0:
            w_union(c.n1, c.n2)
    
    for r in range(15):
        for c in range(2, 6):
            w_union(r * 14 + c, r * 14 + c + 1)
        for c in range(7, 11):
            w_union(r * 14 + c, r * 14 + c + 1)
    
    # Group resistors by their pair of (w_find_endpoint_a, w_find_endpoint_b)
    from collections import defaultdict
    pair_groups = defaultdict(list)
    for i, c in enumerate(used_resistors):
        u = w_find(c.n1)
        v = w_find(c.n2)
        key = tuple(sorted((u, v)))
        pair_groups[key].append(c)
    
    parts = []
    for key, resistors in pair_groups.items():
        if len(resistors) == 1:
            parts.append(f"{resistors[0].value}Ω")
        else:
            vals = "‖".join(str(c.value) for c in resistors)
            parts.append(f"({vals}Ω)" if len(pair_groups) > 1 else f"{vals}Ω")
    
    desc = " + ".join(parts) if len(parts) > 1 else parts[0]
    return [desc]


def draw_board(game, filename, title="Circuit Master - Match Replay", action_log=None, highlight_comps=None):
    """v8.2: board + info panel + portrait objective cards for each player"""
    rows, cols = game.board.layout.shape

    figsize_w = 30 + (cols - 14) * 0.5
    figsize_h = 12 + (rows - 15) * 0.3
    fig = plt.figure(figsize=(figsize_w, figsize_h))

    # ── layout constants ──────────────────────────────────────────────────────
    BOARD_X, BOARD_W         = 0.02, 0.42
    INFO_X,  INFO_W          = 0.46, 0.13
    CARDS_X, CARDS_W         = 0.61, 0.37
    CARD_H, CARD_GAP         = 0.43, 0.005   # height of each card row
    P0_Y, P1_Y               = 0.53, 0.04    # bottom y of P0/P1 card rows
    P0_COLOR, P1_COLOR       = '#d32f2f', '#7b1fa2'
    CARD_W = (CARDS_W - 2 * CARD_GAP) / 3

    # ── 1. BREADBOARD ─────────────────────────────────────────────────────────
    ax_board = fig.add_axes([BOARD_X, 0.05, BOARD_W, 0.90])
    col_labels = ["+", "-", "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "+", "-"]
    col_labels = col_labels[:cols]
    
    for r in range(rows):
        ax_board.text(-1.5, rows - 1 - r, f"{r}", fontsize=11, ha='right', va='center', color='gray')
        for c in range(cols):
            if c in [0, 12]:
                color = 'red'; alpha = 0.8
            elif c in [1, 13]:
                color = 'blue'; alpha = 0.8
            else:
                color = 'gray'; alpha = 0.3
            ax_board.plot(c, rows - 1 - r, 'o', color=color, markersize=5, alpha=alpha)
    
    for c in range(cols):
        if c in [0, 12]:
            color = 'red'
        elif c in [1, 13]:
            color = 'blue'
        else:
            color = 'black'
        if c < len(col_labels):
            ax_board.text(c, rows, col_labels[c], fontsize=12, ha='center', va='bottom', fontweight='bold', color=color)
 
    ax_board.fill_between([6.5, 7.5], -1, rows, color='gray', alpha=0.1)

    for comp in game.placed_components:
        x1, y1 = comp.c1, rows - 1 - comp.r1
        x2, y2 = comp.c2, rows - 1 - comp.r2
        color = '#d32f2f' if comp.owner == 0 else '#7b1fa2'
        linewidth = 5 if not getattr(comp, 'locked', False) else 8
        ax_board.plot([x1, x2], [y1, y2], color=color, linewidth=linewidth, solid_capstyle='round', alpha=0.9)
        mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
        unit = 'µF' if getattr(comp, 'card_type', '') == 'capacitor' else 'Ω'
        label = f"{comp.value}{unit}" if comp.value > 0 else "Wire"
        ax_board.text(mid_x, mid_y + 0.15, label, fontsize=9, ha='center', va='bottom',
                   bbox=dict(facecolor='white', alpha=0.8, edgecolor='none', pad=0.2))

    # Draw auto-connect wires (dashed) for each circuit group of each player
    if hasattr(game, '_identify_circuit_groups') and hasattr(game, '_auto_rail_connections'):
        for pid, color in [(0, '#d32f2f'), (1, '#7b1fa2')]:
            my_comps = [c for c in game.placed_components if c.owner == pid and c.value > 0]
            for group in game._identify_circuit_groups(my_comps):
                for w in game._auto_rail_connections(pid, comps=group):
                    wx1, wy1 = w.c1, rows - 1 - w.r1
                    wx2, wy2 = w.c2, rows - 1 - w.r2
                    ax_board.plot([wx1, wx2], [wy1, wy2], color=color, linewidth=2.5,
                                  linestyle='--', alpha=0.55, solid_capstyle='round')

    # Green highlight overlay for completed circuits
    if highlight_comps:
        highlight_ids = {id(c) for c in highlight_comps}
        for comp in game.placed_components:
            if id(comp) in highlight_ids:
                x1, y1 = comp.c1, rows - 1 - comp.r1
                x2, y2 = comp.c2, rows - 1 - comp.r2
                ax_board.plot([x1, x2], [y1, y2], color='#2e7d32', linewidth=6,
                              solid_capstyle='round', alpha=0.85)

    ax_board.set_title("CIRCUIT SURGE - Breadboard Duel", fontsize=22, fontweight='bold', pad=20)
    ax_board.set_xlim(-2, cols + 1)
    ax_board.set_ylim(-2, rows + 2)
    ax_board.set_aspect('equal')
    ax_board.axis('off')

    # ── 2. INFO PANEL (log + scores + circuit) ────────────────────────────────
    ax_log = fig.add_axes([INFO_X, 0.38, INFO_W, 0.57])
    ax_log.set_title("ACTION LOG", fontsize=11, fontweight='bold', pad=4)
    if action_log:
        for i, entry in enumerate(action_log[-13:]):
            if "✓" in entry:
                c = '#2e7d32'
            elif "P1" in entry:
                c = P0_COLOR
            else:
                c = P1_COLOR
            ax_log.text(0.05, 0.96 - i * 0.072, entry[:55], fontsize=7.5,
                        transform=ax_log.transAxes, color=c)
    ax_log.set_xlim(0, 1); ax_log.set_ylim(0, 1); ax_log.axis('off')

    ax_info = fig.add_axes([INFO_X, 0.05, INFO_W, 0.30])
    ax_info.set_title("SCORES", fontsize=11, fontweight='bold', pad=4)
    ax_info.text(0.08, 0.88, f"P0: {game.scores[0]} pts", fontsize=15,
                 color=P0_COLOR, fontweight='bold', transform=ax_info.transAxes)
    ax_info.text(0.08, 0.72, f"P1: {game.scores[1]} pts", fontsize=15,
                 color=P1_COLOR, fontweight='bold', transform=ax_info.transAxes)
    co = getattr(game, 'completed_objectives', [[], []])
    n_done_0 = len(co[0])
    n_done_1 = len(co[1])
    ax_info.text(0.08, 0.54, f"P0 done: {n_done_0}", fontsize=10,
                 color='gray', transform=ax_info.transAxes)
    ax_info.text(0.08, 0.42, f"P1 done: {n_done_1}", fontsize=10,
                 color='gray', transform=ax_info.transAxes)
    req, used, plus, minus = game.calculate_graph_equivalent()
    rail_status = "✓ rails OK" if plus and minus else "✗ open"
    ax_info.text(0.08, 0.24, f"Req={req:.1f}Ω", fontsize=10,
                 color='#555', transform=ax_info.transAxes)
    ax_info.text(0.08, 0.10, rail_status, fontsize=9,
                 color='gray', transform=ax_info.transAxes)
    ax_info.set_xlim(0, 1); ax_info.set_ylim(0, 1); ax_info.axis('off')

    # ── 3. OBJECTIVE CARDS ────────────────────────────────────────────────────
    def _draw_player_cards(pid, row_y, p_color, label):
        fig.text(CARDS_X, row_y + CARD_H + 0.005, label,
                 fontsize=11, fontweight='bold', color=p_color, va='bottom')
        obj_store = getattr(game, 'objectives', [[], []])
        objs = obj_store[pid] if isinstance(obj_store, list) else obj_store.get(pid, [])
        for i in range(3):
            ax_c = fig.add_axes([CARDS_X + i * (CARD_W + CARD_GAP), row_y, CARD_W, CARD_H])
            if i < len(objs):
                _draw_objective_card(ax_c, objs[i], p_color)
            else:
                ax_c.set_xlim(0, 10); ax_c.set_ylim(0, 10); ax_c.axis('off')
                ax_c.add_patch(plt.Rectangle((0.3, 0.3), 9.4, 9.4, fill=False,
                                             edgecolor='#ccc', lw=1.2, ls='--'))

    _draw_player_cards(0, P0_Y, P0_COLOR, "P0 OBJECTIVES")
    _draw_player_cards(1, P1_Y, P1_COLOR, "P1 OBJECTIVES")

    plt.suptitle(title, fontsize=22, fontweight='bold', y=0.995)
    fig.savefig(filename, dpi=80, bbox_inches='tight')
    plt.close(fig)
