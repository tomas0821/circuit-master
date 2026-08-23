"""
Generate educational circuit example PNGs using the exact game board style.
Outputs:
  card_images/example_series.png      — two 100Ω resistors in series  (200Ω)
  card_images/example_parallel.png    — two 100Ω resistors in parallel (50Ω)
  card_images/example_series_es.png   — Spanish version
  card_images/example_parallel_es.png — Spanish version
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import os

from generate_plots import _draw_element

OUT_DIR = 'card_images'
os.makedirs(OUT_DIR, exist_ok=True)

ROWS, COLS = 15, 14
COL_LABELS = ["+", "−", "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "+", "−"]

P1_COLOR  = '#c62828'   # player 1 red
RAIL_POS  = '#e53935'   # + rail red
RAIL_NEG  = '#1565c0'   # − rail blue
CONNECT   = '#2e7d32'   # dashed connect-to-rail arrow color
ROWRAIL   = '#ff8f00'   # row-rail highlight (internal connection)
HOLE_GRAY = '#9e9e9e'


def y(row):
    """Convert board row → display y (row 0 at top)."""
    return ROWS - 1 - row


def draw_board_base(ax, ravine_label="RAVINE"):
    """Draw the blank board: holes, rails, labels, ravine."""

    # ── ravine ────────────────────────────────────────────────────────────────
    ax.fill_between([6.45, 7.55], -0.5, ROWS - 0.5,
                    color='#bdbdbd', alpha=0.25, zorder=0)
    ax.text(7.0, ROWS + 0.15, ravine_label, ha='center', va='bottom',
            fontsize=7, color='#757575', style='italic')

    # ── holes ─────────────────────────────────────────────────────────────────
    for r in range(ROWS):
        for c in range(COLS):
            if c in [0, 12]:
                col, alpha, ms = RAIL_POS, 0.85, 7
            elif c in [1, 13]:
                col, alpha, ms = RAIL_NEG, 0.85, 7
            else:
                col, alpha, ms = HOLE_GRAY, 0.35, 5
            ax.plot(c, y(r), 'o', color=col, markersize=ms, alpha=alpha, zorder=2)

    # ── column labels ─────────────────────────────────────────────────────────
    for c, lbl in enumerate(COL_LABELS):
        col = RAIL_POS if c in [0, 12] else (RAIL_NEG if c in [1, 13] else 'black')
        ax.text(c, ROWS - 0.2, lbl, ha='center', va='bottom',
                fontsize=11, fontweight='bold', color=col)

    # ── row numbers ───────────────────────────────────────────────────────────
    for r in range(ROWS):
        ax.text(-1.2, y(r), str(r), ha='right', va='center',
                fontsize=8.5, color='#bdbdbd')

    ax.set_xlim(-2.0, COLS + 0.5)
    ax.set_ylim(-1.0, ROWS + 0.5)
    ax.set_aspect('equal')
    ax.axis('off')


def draw_component(ax, r1, c1, r2, c2, value, color=P1_COLOR):
    """Draw a single resistor as a thick line with a value label."""
    x1, x2 = c1, c2
    y1, y2 = y(r1), y(r2)
    ax.plot([x1, x2], [y1, y2], color=color, lw=7,
            solid_capstyle='round', zorder=4)
    # label offset to the right
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    ax.text(mx + 0.55, my, f"{value} Ω",
            ha='left', va='center', fontsize=10, fontweight='bold',
            color=color, zorder=5,
            bbox=dict(facecolor='white', alpha=0.85, edgecolor='none', pad=1))


def draw_rowrail(ax, row, c_start, c_end):
    """Highlight the internal row-rail connection between columns c_start–c_end."""
    yd = y(row)
    ax.plot([c_start, c_end], [yd, yd], color=ROWRAIL, lw=4,
            alpha=0.55, solid_capstyle='round', zorder=3)
    # small dots at each hole
    for c in range(c_start, c_end + 1):
        ax.plot(c, yd, 'o', color=ROWRAIL, markersize=7, alpha=0.7, zorder=3)


def draw_connect(ax, row, col_hole, rail_col, label="Connect\nto Rail"):
    """Draw a dashed arrow from a hole to the + or − rail (Connect action)."""
    y_row = y(row)
    ax.annotate("",
        xy=(rail_col, y_row), xytext=(col_hole, y_row),
        arrowprops=dict(
            arrowstyle="-|>",
            color=CONNECT, lw=1.8,
            linestyle='dashed',
            connectionstyle='arc3,rad=0.0',
        ), zorder=6)
    # label above the midpoint
    mx = (col_hole + rail_col) / 2
    ax.text(mx, y_row + 0.45, label, ha='center', va='bottom',
            fontsize=7.5, color=CONNECT, style='italic',
            bbox=dict(facecolor='white', alpha=0.75, edgecolor='none', pad=0))


def draw_schematic(ax, topo, title_text, formula_text, color):
    """Draw a circuit schematic + formula on a plain axes."""
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis('off')
    ax.set_facecolor('#fafafa')
    for spine in ax.spines.values():
        spine.set_visible(False)

    ax.text(5, 9.4, title_text, ha='center', va='top',
            fontsize=12, fontweight='bold', color=color)

    _draw_element(ax, topo, x0=0.5, x1=9.5, yc=5.5, yspan=4.5,
                  lw=2.2, fsize=10, color='#212121')

    ax.text(5, 1.5, formula_text, ha='center', va='center',
            fontsize=13, color=color, fontweight='bold',
            bbox=dict(facecolor='white', edgecolor=color, lw=1.5,
                      boxstyle='round,pad=0.4'))


# ─────────────────────────────────────────────────────────────────────────────
# FIGURE 1: SERIES
# ─────────────────────────────────────────────────────────────────────────────

def make_series():
    fig = plt.figure(figsize=(18, 10), facecolor='white')
    fig.suptitle("Series Circuit — 100 Ω + 100 Ω = 200 Ω",
                 fontsize=18, fontweight='bold', y=0.98)

    # ── board panel ───────────────────────────────────────────────────────────
    ax_board = fig.add_axes([0.02, 0.07, 0.58, 0.87])
    draw_board_base(ax_board)

    # Two 100Ω resistors stacked vertically in column A (col 2), rows 1-2 and 2-3
    draw_component(ax_board, r1=1, c1=2, r2=2, c2=2, value=100)
    draw_component(ax_board, r1=2, c1=2, r2=3, c2=2, value=100)

    # Row-rail of the shared node (row 2) — just shows the hole is part of the rail
    draw_rowrail(ax_board, row=2, c_start=2, c_end=6)

    # Connect to − rail (col 1) from the top node (row 1)
    draw_connect(ax_board, row=1, col_hole=2, rail_col=1, label="Connect\nto − rail")

    # Connect to + rail (col 0) from the bottom node (row 3)
    draw_connect(ax_board, row=3, col_hole=2, rail_col=0, label="Connect\nto + rail")

    # Annotations
    ax_board.text(3.0, y(1), "① Top node → − rail", ha='left', va='center',
                  fontsize=11, color=RAIL_NEG,
                  bbox=dict(facecolor='white', alpha=0.8, edgecolor='none', pad=1))
    ax_board.text(3.0, y(2), "② Shared node (connected internally)", ha='left', va='center',
                  fontsize=11, color=ROWRAIL,
                  bbox=dict(facecolor='white', alpha=0.8, edgecolor='none', pad=1))
    ax_board.text(3.0, y(3), "③ Bottom node → + rail", ha='left', va='center',
                  fontsize=11, color=RAIL_POS,
                  bbox=dict(facecolor='white', alpha=0.8, edgecolor='none', pad=1))

    ax_board.set_aspect('auto')
    ax_board.set_xlim(-2.0, 9.5)
    ax_board.set_ylim(y(5) - 0.5, y(0) + 0.9)
    ax_board.set_title("Game Board", fontsize=13, color='#444', pad=6)

    # ── schematic + formula panel ─────────────────────────────────────────────
    ax_sch = fig.add_axes([0.62, 0.35, 0.36, 0.55])
    draw_schematic(
        ax_sch,
        topo=('series', [('R', 100), ('R', 100)]),
        title_text="Circuit Schematic",
        formula_text="R_eq = R₁ + R₂ = 100 + 100 = 200 Ω",
        color=P1_COLOR,
    )

    # ── rule box ──────────────────────────────────────────────────────────────
    ax_rule = fig.add_axes([0.62, 0.07, 0.36, 0.26])
    ax_rule.axis('off')
    ax_rule.set_facecolor('#fff8e1')
    ax_rule.add_patch(mpatches.FancyBboxPatch(
        (0.02, 0.05), 0.96, 0.90,
        boxstyle='round,pad=0.02', facecolor='#fff8e1',
        edgecolor='#f9a825', lw=1.5, transform=ax_rule.transAxes))
    rule_text = (
        "HOW TO BUILD A SERIES CIRCUIT\n\n"
        "1. In your zone, place two resistors in the same\n"
        "   column in consecutive rows (e.g. rows 1→2, 2→3).\n\n"
        "2. The shared middle hole connects them automatically\n"
        "   (all holes in the same row half are linked).\n\n"
        "3. Complete Objective (1 PA): connect top hole to\n"
        "   the − rail and bottom hole to the + rail.\n"
        "   Write the equivalent value on the objective card."
    )
    ax_rule.text(0.08, 0.88, rule_text, ha='left', va='top',
                 fontsize=9.5, color='#333', transform=ax_rule.transAxes,
                 linespacing=1.5)

    fig.savefig(os.path.join(OUT_DIR, 'example_series.png'),
                dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print("Saved example_series.png")


# ─────────────────────────────────────────────────────────────────────────────
# FIGURE 2: PARALLEL
# ─────────────────────────────────────────────────────────────────────────────

def make_parallel():
    fig = plt.figure(figsize=(18, 10), facecolor='white')
    fig.suptitle("Parallel Circuit — 100 Ω ∥ 100 Ω = 50 Ω",
                 fontsize=18, fontweight='bold', y=0.98)

    # ── board panel ───────────────────────────────────────────────────────────
    ax_board = fig.add_axes([0.02, 0.07, 0.58, 0.87])
    draw_board_base(ax_board)

    # Two 100Ω resistors side-by-side in adjacent columns, same row pair (rows 1-2)
    draw_component(ax_board, r1=1, c1=2, r2=2, c2=2, value=100)  # col A
    draw_component(ax_board, r1=1, c1=3, r2=2, c2=3, value=100)  # col B

    # Row-rails at rows 1 and 2 (showing both top and bottom nodes are shared)
    draw_rowrail(ax_board, row=1, c_start=2, c_end=6)
    draw_rowrail(ax_board, row=2, c_start=2, c_end=6)

    # Connect top row (row 1) to − rail
    draw_connect(ax_board, row=1, col_hole=2, rail_col=1, label="Connect\nto − rail")

    # Connect bottom row (row 2) to + rail
    draw_connect(ax_board, row=2, col_hole=2, rail_col=0, label="Connect\nto + rail")

    # Annotations
    ax_board.text(4.2, y(1), "① Top row (1) — both tops share this rail\n"
                              "   → connected to − rail via Connect action",
                  ha='left', va='center', fontsize=9, color=ROWRAIL,
                  bbox=dict(facecolor='white', alpha=0.8, edgecolor='none', pad=1))
    ax_board.text(4.2, y(2) - 0.15, "② Bottom row (2) — both bottoms share this rail\n"
                                     "   → connected to + rail via Connect action",
                  ha='left', va='center', fontsize=9, color=ROWRAIL,
                  bbox=dict(facecolor='white', alpha=0.8, edgecolor='none', pad=1))

    ax_board.set_aspect('auto')
    ax_board.set_xlim(-2.0, 9.5)
    ax_board.set_ylim(y(4) - 0.5, y(0) + 0.9)
    ax_board.set_title("Game Board", fontsize=13, color='#444', pad=6)

    # ── schematic + formula panel ─────────────────────────────────────────────
    ax_sch = fig.add_axes([0.62, 0.35, 0.36, 0.55])
    draw_schematic(
        ax_sch,
        topo=('parallel', [('R', 100), ('R', 100)]),
        title_text="Circuit Schematic",
        formula_text="R_eq = (R₁ × R₂)/(R₁ + R₂) = 10000/200 = 50 Ω",
        color=P1_COLOR,
    )

    # ── rule box ──────────────────────────────────────────────────────────────
    ax_rule = fig.add_axes([0.62, 0.07, 0.36, 0.26])
    ax_rule.axis('off')
    ax_rule.add_patch(mpatches.FancyBboxPatch(
        (0.02, 0.05), 0.96, 0.90,
        boxstyle='round,pad=0.02', facecolor='#e8f5e9',
        edgecolor='#388e3c', lw=1.5, transform=ax_rule.transAxes))
    rule_text = (
        "HOW TO BUILD A PARALLEL CIRCUIT\n\n"
        "1. In your zone, place two resistors in adjacent\n"
        "   columns (e.g. A and B), same pair of rows (1→2).\n\n"
        "2. Holes A–E in the same row are internally connected,\n"
        "   so both tops share one node and both bottoms another.\n\n"
        "3. Complete Objective (1 PA): connect the top row to\n"
        "   the − rail and bottom row to the + rail.\n"
        "   Write the equivalent value on the objective card."
    )
    ax_rule.text(0.08, 0.88, rule_text, ha='left', va='top',
                 fontsize=9.5, color='#333', transform=ax_rule.transAxes,
                 linespacing=1.5)

    fig.savefig(os.path.join(OUT_DIR, 'example_parallel.png'),
                dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print("Saved example_parallel.png")


def make_series_es():
    fig = plt.figure(figsize=(18, 10), facecolor='white')
    fig.suptitle("Circuito en Serie — 100 Ω + 100 Ω = 200 Ω",
                 fontsize=18, fontweight='bold', y=0.98)

    ax_board = fig.add_axes([0.02, 0.07, 0.58, 0.87])
    draw_board_base(ax_board, ravine_label="RANURA")

    draw_component(ax_board, r1=1, c1=2, r2=2, c2=2, value=100)
    draw_component(ax_board, r1=2, c1=2, r2=3, c2=2, value=100)
    draw_rowrail(ax_board, row=2, c_start=2, c_end=6)
    draw_connect(ax_board, row=1, col_hole=2, rail_col=1, label="Conectar\na riel −")
    draw_connect(ax_board, row=3, col_hole=2, rail_col=0, label="Conectar\na riel +")

    ax_board.text(3.0, y(1), "① Nodo superior → riel −", ha='left', va='center',
                  fontsize=9, color=RAIL_NEG,
                  bbox=dict(facecolor='white', alpha=0.8, edgecolor='none', pad=1))
    ax_board.text(3.0, y(2), "② Nodo compartido (conexión interna de fila)", ha='left', va='center',
                  fontsize=9, color=ROWRAIL,
                  bbox=dict(facecolor='white', alpha=0.8, edgecolor='none', pad=1))
    ax_board.text(3.0, y(3), "③ Nodo inferior → riel +", ha='left', va='center',
                  fontsize=9, color=RAIL_POS,
                  bbox=dict(facecolor='white', alpha=0.8, edgecolor='none', pad=1))
    ax_board.set_aspect('auto')
    ax_board.set_xlim(-2.0, 9.5)
    ax_board.set_ylim(y(5) - 0.5, y(0) + 0.9)
    ax_board.set_title("Tablero de Juego", fontsize=13, color='#444', pad=6)

    ax_sch = fig.add_axes([0.62, 0.35, 0.36, 0.55])
    draw_schematic(
        ax_sch,
        topo=('series', [('R', 100), ('R', 100)]),
        title_text="Esquema del Circuito",
        formula_text="R_eq = R₁ + R₂ = 100 + 100 = 200 Ω",
        color=P1_COLOR,
    )

    ax_rule = fig.add_axes([0.62, 0.07, 0.36, 0.26])
    ax_rule.axis('off')
    ax_rule.add_patch(mpatches.FancyBboxPatch(
        (0.02, 0.05), 0.96, 0.90,
        boxstyle='round,pad=0.02', facecolor='#fff8e1',
        edgecolor='#f9a825', lw=1.5, transform=ax_rule.transAxes))
    rule_text = (
        "CÓMO CONSTRUIR UN CIRCUITO EN SERIE\n\n"
        "1. En tu zona: misma columna, filas consecutivas\n"
        "   (ej. filas 1→2 y 2→3).\n\n"
        "2. El orificio del medio los conecta automáticamente\n"
        "   (todos los orificios de la misma media fila están unidos).\n\n"
        "3. Completar Objetivo (1 PA): conecta el nodo\n"
        "   superior al riel − y el inferior al riel +.\n"
        "   Anota el valor equivalente en la carta."
    )
    ax_rule.text(0.08, 0.88, rule_text, ha='left', va='top',
                 fontsize=9.5, color='#333', transform=ax_rule.transAxes,
                 linespacing=1.5)

    fig.savefig(os.path.join(OUT_DIR, 'example_series_es.png'),
                dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print("Saved example_series_es.png")


def make_parallel_es():
    fig = plt.figure(figsize=(18, 10), facecolor='white')
    fig.suptitle("Circuito en Paralelo — 100 Ω ∥ 100 Ω = 50 Ω",
                 fontsize=18, fontweight='bold', y=0.98)

    ax_board = fig.add_axes([0.02, 0.07, 0.58, 0.87])
    draw_board_base(ax_board, ravine_label="RANURA")

    draw_component(ax_board, r1=1, c1=2, r2=2, c2=2, value=100)
    draw_component(ax_board, r1=1, c1=3, r2=2, c2=3, value=100)
    draw_rowrail(ax_board, row=1, c_start=2, c_end=6)
    draw_rowrail(ax_board, row=2, c_start=2, c_end=6)
    draw_connect(ax_board, row=1, col_hole=2, rail_col=1, label="Conectar\na riel −")
    draw_connect(ax_board, row=2, col_hole=2, rail_col=0, label="Conectar\na riel +")

    ax_board.text(4.2, y(1), "① Fila superior (1) — ambos extremos comparten este riel\n"
                              "   → conectado al riel − con la acción Conectar",
                  ha='left', va='center', fontsize=9, color=ROWRAIL,
                  bbox=dict(facecolor='white', alpha=0.8, edgecolor='none', pad=1))
    ax_board.text(4.2, y(2) - 0.15, "② Fila inferior (2) — ambos extremos comparten este riel\n"
                                     "   → conectado al riel + con la acción Conectar",
                  ha='left', va='center', fontsize=9, color=ROWRAIL,
                  bbox=dict(facecolor='white', alpha=0.8, edgecolor='none', pad=1))
    ax_board.set_aspect('auto')
    ax_board.set_xlim(-2.0, 9.5)
    ax_board.set_ylim(y(4) - 0.5, y(0) + 0.9)
    ax_board.set_title("Tablero de Juego", fontsize=13, color='#444', pad=6)

    ax_sch = fig.add_axes([0.62, 0.35, 0.36, 0.55])
    draw_schematic(
        ax_sch,
        topo=('parallel', [('R', 100), ('R', 100)]),
        title_text="Esquema del Circuito",
        formula_text="R_eq = (R₁ × R₂)/(R₁ + R₂) = 10000/200 = 50 Ω",
        color=P1_COLOR,
    )

    ax_rule = fig.add_axes([0.62, 0.07, 0.36, 0.26])
    ax_rule.axis('off')
    ax_rule.add_patch(mpatches.FancyBboxPatch(
        (0.02, 0.05), 0.96, 0.90,
        boxstyle='round,pad=0.02', facecolor='#e8f5e9',
        edgecolor='#388e3c', lw=1.5, transform=ax_rule.transAxes))
    rule_text = (
        "CÓMO CONSTRUIR UN CIRCUITO EN PARALELO\n\n"
        "1. En tu zona: columnas adyacentes (ej. A y B),\n"
        "   en exactamente el mismo par de filas (ej. 1→2).\n\n"
        "2. Los orificios A–E de la misma fila están conectados internamente,\n"
        "   así ambos extremos superiores comparten un nodo.\n\n"
        "3. Completar Objetivo (1 PA): conecta la fila\n"
        "   superior al riel − y la inferior al riel +.\n"
        "   Anota el valor equivalente en la carta."
    )
    ax_rule.text(0.08, 0.88, rule_text, ha='left', va='top',
                 fontsize=9.5, color='#333', transform=ax_rule.transAxes,
                 linespacing=1.5)

    fig.savefig(os.path.join(OUT_DIR, 'example_parallel_es.png'),
                dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print("Saved example_parallel_es.png")


if __name__ == '__main__':
    make_series()
    make_parallel()
    make_series_es()
    make_parallel_es()
    print("Done.")
