"""
Generate a printable deck of Circuit Master cards — Spanish version.
Output: deck_a4_fronts_es.pdf, deck_a4_backs_es.pdf, deck_a4_print_es.pdf,
        components_a4_fronts_es.pdf, components_a4_backs_es.pdf, components_a4_print_es.pdf,
        deck_objective_cards_es.png
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.image as mpimg
import numpy as np
import os
from generate_plots import _TOPOLOGIES, _max_parallel_branches, _draw_element

LOGO_PATH = os.path.join(os.path.dirname(__file__),
                         'Gemini_Generated_Image_lno85mlno85mlno8.png')

SUBTITLE = "Un Juego Educativo de Electrónica"

# ── card definitions (all 24 unique objective types) ─────────────────────────
CARDS = [
    # ── 2-component resistance (PREPARACIÓN tier) ────────────────────────────
    dict(route_desc="Series 200Ω",    target_req=200,    points=30, obj_type="resistance", n=2),
    dict(route_desc="Parallel 50Ω",   target_req=50,     points=30, obj_type="resistance", n=2),
    dict(route_desc="Series 300Ω",    target_req=300,    points=30, obj_type="resistance", n=2),
    dict(route_desc="Parallel 67Ω",   target_req=66.67,  points=30, obj_type="resistance", n=2),
    dict(route_desc="Series 400Ω",    target_req=400,    points=35, obj_type="resistance", n=2),
    dict(route_desc="Parallel 75Ω",   target_req=75,     points=30, obj_type="resistance", n=2),
    dict(route_desc="Series 500Ω",    target_req=500,    points=40, obj_type="resistance", n=2),
    dict(route_desc="Parallel 120Ω",  target_req=120,    points=35, obj_type="resistance", n=2),
    # ── 3-component resistance (CONSTRUCCIÓN tier) ───────────────────────────
    dict(route_desc="3-Parallel 33Ω", target_req=33.33,  points=40, obj_type="resistance", n=3),
    dict(route_desc="Mixed 250Ω",     target_req=250,    points=45, obj_type="resistance", n=3),
    dict(route_desc="Mixed 350Ω",     target_req=350,    points=45, obj_type="resistance", n=3),
    dict(route_desc="Mixed 167Ω",     target_req=166.67, points=45, obj_type="resistance", n=3),
    dict(route_desc="Mixed 175Ω",     target_req=175,    points=45, obj_type="resistance", n=3),
    dict(route_desc="Mixed 220Ω",     target_req=220,    points=45, obj_type="resistance", n=3),
    # ── 4-component resistance (EXPERTO tier) ────────────────────────────────
    dict(route_desc="Bridge 100Ω",    target_req=100,    points=65, obj_type="resistance", n=4),
    dict(route_desc="Mixed 133Ω",     target_req=133.33, points=65, obj_type="resistance", n=4),
    # ── capacitance (CAP tier) ────────────────────────────────────────────────
    dict(route_desc="Series 5µF",      target_req=5,     points=30, obj_type="capacitance", n=2),
    dict(route_desc="Series 6.7µF",    target_req=6.67,  points=30, obj_type="capacitance", n=2),
    dict(route_desc="Series 7.5µF",    target_req=7.5,   points=30, obj_type="capacitance", n=2),
    dict(route_desc="Series 12µF",     target_req=12,    points=35, obj_type="capacitance", n=2),
    dict(route_desc="Series 10µF",     target_req=10,    points=30, obj_type="capacitance", n=2),
    dict(route_desc="Parallel 20µF",   target_req=20,    points=30, obj_type="capacitance", n=2),
    dict(route_desc="Parallel 40µF",   target_req=40,    points=35, obj_type="capacitance", n=2),
    dict(route_desc="Parallel 50µF",   target_req=50,    points=35, obj_type="capacitance", n=2),
    dict(route_desc="Series 3.3µF",    target_req=3.33,  points=35, obj_type="capacitance", n=3),
    dict(route_desc="Series 4µF",      target_req=4,     points=40, obj_type="capacitance", n=3),
    dict(route_desc="Series 6µF",      target_req=6,     points=40, obj_type="capacitance", n=3),
    dict(route_desc="Mixed 8µF",       target_req=8,     points=45, obj_type="capacitance", n=3),
    dict(route_desc="Mixed 13.3µF",    target_req=13.33, points=45, obj_type="capacitance", n=3),
    dict(route_desc="3-Parallel 60µF", target_req=60,    points=45, obj_type="capacitance", n=3),
    dict(route_desc="Series 2.5µF",    target_req=2.5,   points=65, obj_type="capacitance", n=4),
    dict(route_desc="Series 3µF",      target_req=3,     points=65, obj_type="capacitance", n=4),
]

# Tier palette — Spanish tier names
def _tier(obj_type, n):
    if n == 4:
        tier = "EXPERTO"
    elif n == 3:
        tier = "CONSTRUCCIÓN"
    else:
        tier = "PREPARACIÓN"
    if obj_type == "capacitance":
        color = {'PREPARACIÓN': '#0288d1', 'CONSTRUCCIÓN': '#00838f', 'EXPERTO': '#1a237e'}[tier]
        return tier, color
    if n == 4:
        return tier, '#6a1b9a'
    if n == 3:
        return tier, '#e65100'
    return         tier, '#2e7d32'


def draw_deck_card(ax, route_desc, target_req, points, obj_type="resistance", n=2):
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 14)
    ax.axis('off')

    tier_label, color = _tier(obj_type, n)

    ax.add_patch(plt.Rectangle((0, 0), 10, 14,
                               facecolor='white', edgecolor=color, lw=2.0, zorder=1))

    ax.add_patch(plt.Rectangle((0, 11.2), 10, 2.8,
                               facecolor=color, edgecolor='none', zorder=2))
    unit = "µF" if obj_type == "capacitance" else "Ω"
    ax.text(1.2, 12.75, "=",
            ha='left', va='center', fontsize=13, fontweight='bold',
            color='white', alpha=0.7, zorder=3)
    ax.plot([2.0, 8.3], [12.55, 12.55], color='white', lw=1.5, alpha=0.7, zorder=3)
    ax.text(8.7, 12.75, unit,
            ha='left', va='center', fontsize=11, fontweight='bold',
            color='white', alpha=0.7, zorder=3)
    ax.text(0.4, 13.6, tier_label,
            ha='left', va='top', fontsize=6, fontweight='bold',
            color='white', alpha=0.85, zorder=3)
    ax.text(9.6, 13.6, f"×{n}",
            ha='right', va='top', fontsize=7, fontweight='bold',
            color='white', alpha=0.85, zorder=3)

    topo = _TOPOLOGIES.get(route_desc)
    if topo:
        max_n = _max_parallel_branches(topo)
        yspan = min(7.0, max(3.0, max_n * 2.1))
        yc = 6.8
        _draw_element(ax, topo, 0.7, 9.3, yc, yspan, lw=1.8, fsize=8.0, color='#1a1a1a')
    else:
        ax.text(5, 6.5, route_desc, ha='center', va='center', fontsize=9, color='#555')

    ax.plot([0.4, 9.6], [2.8, 2.8], color=color, lw=0.8, alpha=0.4, zorder=2)

    ax.add_patch(plt.Rectangle((0, 0), 10, 2.8,
                               facecolor=color, alpha=0.10, edgecolor='none', zorder=2))

    ax.add_patch(plt.Circle((8.4, 1.4), 1.05,
                             facecolor=color, edgecolor='none', alpha=0.90, zorder=3))
    ax.text(8.4, 1.55, str(points),
            ha='center', va='center', fontsize=13, fontweight='bold',
            color='white', zorder=4)
    ax.text(8.4, 0.45, "pts",
            ha='center', va='center', fontsize=6.5,
            color='white', alpha=0.85, zorder=4)

    icon_lw = 1.4
    icon_y = 1.4
    spacing = 1.5
    x_start = 0.9
    for i in range(n):
        ix = x_start + i * spacing
        if obj_type == "resistance":
            h, dz = 0.28, 0.10
            zx = [ix, ix+dz, ix+2*dz, ix+3*dz, ix+4*dz, ix+5*dz, ix+6*dz]
            zy = [icon_y, icon_y+h, icon_y-h, icon_y+h, icon_y-h, icon_y+h, icon_y]
            ax.plot(zx, zy, color=color, lw=icon_lw,
                    solid_capstyle='round', solid_joinstyle='round', zorder=3)
        else:
            mid = ix + 0.3
            gap = 0.07
            cap_h = 0.38
            ax.plot([ix, mid - gap], [icon_y, icon_y], color=color, lw=icon_lw, zorder=3)
            ax.plot([mid + gap, ix + 0.6], [icon_y, icon_y], color=color, lw=icon_lw, zorder=3)
            ax.plot([mid-gap, mid-gap], [icon_y-cap_h/2, icon_y+cap_h/2],
                    color=color, lw=icon_lw*2, solid_capstyle='butt', zorder=3)
            ax.plot([mid+gap, mid+gap], [icon_y-cap_h/2, icon_y+cap_h/2],
                    color=color, lw=icon_lw*2, solid_capstyle='butt', zorder=3)


def draw_card_back(ax):
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 14)
    ax.axis('off')

    TEAL   = '#0d7f7a'
    ORANGE = '#e87722'
    BG     = '#ffffff'

    ax.add_patch(plt.Rectangle((0, 0), 10, 14,
                               facecolor=BG, edgecolor='none', zorder=1))
    ax.add_patch(plt.Rectangle((0.15, 0.15), 9.7, 13.7,
                               fill=False, edgecolor=TEAL, lw=2.5, zorder=5))
    ax.add_patch(plt.Rectangle((0.45, 0.45), 9.1, 13.1,
                               fill=False, edgecolor=ORANGE, lw=0.8, alpha=0.7, zorder=5))

    def corner(cx, cy, sx, sy):
        ax.plot([cx, cx + sx * 0.6], [cy, cy],
                color=ORANGE, lw=1.6, solid_capstyle='round', zorder=6)
        ax.plot([cx, cx], [cy, cy + sy * 0.6],
                color=ORANGE, lw=1.6, solid_capstyle='round', zorder=6)
        ax.plot(cx + sx * 0.6, cy, 'o', color=TEAL, markersize=3.5, zorder=7)
        ax.plot(cx, cy + sy * 0.6, 'o', color=TEAL, markersize=3.5, zorder=7)

    corner(0.75, 0.75,  1,  1)
    corner(9.25, 0.75, -1,  1)
    corner(0.75, 13.25,  1, -1)
    corner(9.25, 13.25, -1, -1)

    if os.path.exists(LOGO_PATH):
        logo = mpimg.imread(LOGO_PATH)
        h_px, w_px = logo.shape[:2]
        logo_w = 7.6
        logo_h = logo_w * h_px / w_px
        logo_x0 = (10 - logo_w) / 2
        logo_y0 = 4.0
        ax.add_patch(plt.Rectangle((logo_x0, logo_y0), logo_w, logo_h,
                                   facecolor='white', edgecolor='none', zorder=3))
        ax.imshow(logo, extent=[logo_x0, logo_x0 + logo_w,
                                 logo_y0, logo_y0 + logo_h],
                  aspect='auto', zorder=4)

    ax.add_patch(plt.Rectangle((0.15, 0.15), 9.7, 2.1,
                               facecolor=TEAL, edgecolor='none', alpha=0.92, zorder=5))
    ax.text(5, 1.55, "CARTA OBJETIVO",
            ha='center', va='center', fontsize=9, fontweight='bold',
            color='white', zorder=6)
    ax.text(5, 0.75, SUBTITLE,
            ha='center', va='center', fontsize=6, color='white', alpha=0.85, zorder=6)


def draw_component_back(ax):
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 14)
    ax.axis('off')

    DARK   = '#263238'
    AMBER  = '#e67e00'
    BG     = '#ffffff'

    ax.add_patch(plt.Rectangle((0, 0), 10, 14,
                               facecolor=BG, edgecolor='none', zorder=1))
    ax.add_patch(plt.Rectangle((0.15, 0.15), 9.7, 13.7,
                               fill=False, edgecolor=DARK, lw=2.5, zorder=5))
    ax.add_patch(plt.Rectangle((0.45, 0.45), 9.1, 13.1,
                               fill=False, edgecolor=AMBER, lw=0.8, alpha=0.7, zorder=5))

    def corner(cx, cy, sx, sy):
        ax.plot([cx, cx + sx * 0.6], [cy, cy],
                color=AMBER, lw=1.6, solid_capstyle='round', zorder=6)
        ax.plot([cx, cx], [cy, cy + sy * 0.6],
                color=AMBER, lw=1.6, solid_capstyle='round', zorder=6)
        ax.plot(cx + sx * 0.6, cy, 'o', color=DARK, markersize=3.5, zorder=7)
        ax.plot(cx, cy + sy * 0.6, 'o', color=DARK, markersize=3.5, zorder=7)

    corner(0.75, 0.75,  1,  1)
    corner(9.25, 0.75, -1,  1)
    corner(0.75, 13.25,  1, -1)
    corner(9.25, 13.25, -1, -1)

    if os.path.exists(LOGO_PATH):
        logo = mpimg.imread(LOGO_PATH)
        h_px, w_px = logo.shape[:2]
        logo_w = 7.6
        logo_h = logo_w * h_px / w_px
        logo_x0 = (10 - logo_w) / 2
        logo_y0 = 4.0
        ax.add_patch(plt.Rectangle((logo_x0, logo_y0), logo_w, logo_h,
                                   facecolor='white', edgecolor='none', zorder=3))
        ax.imshow(logo, extent=[logo_x0, logo_x0 + logo_w,
                                 logo_y0, logo_y0 + logo_h],
                  aspect='auto', zorder=4)

    ax.add_patch(plt.Rectangle((0.15, 0.15), 9.7, 2.1,
                               facecolor=DARK, edgecolor='none', alpha=0.92, zorder=5))
    ax.text(5, 1.55, "CARTA DE COMPONENTE",
            ha='center', va='center', fontsize=9, fontweight='bold',
            color='white', zorder=6)
    ax.text(5, 0.75, SUBTITLE,
            ha='center', va='center', fontsize=6, color='white', alpha=0.85, zorder=6)


# ── layout constants ──────────────────────────────────────────────────────────
CARD_W = 2.5
CARD_H = 3.5

import math
from matplotlib.backends.backend_pdf import PdfPages

A4_W, A4_H  = 8.27, 11.69
COLS_PAGE   = 3
ROWS_PAGE   = 3
PER_PAGE    = COLS_PAGE * ROWS_PAGE

GAP_X  = 0.10
GAP_Y  = 0.10
TITLE_H = 0.38
GRID_W  = COLS_PAGE * CARD_W + (COLS_PAGE - 1) * GAP_X
GRID_H  = ROWS_PAGE * CARD_H + (ROWS_PAGE - 1) * GAP_Y
MARGIN_X = (A4_W - GRID_W) / 2
MARGIN_Y = (A4_H - GRID_H - TITLE_H) / 2

n_pages = math.ceil(len(CARDS) / PER_PAGE)

def _add_crop_marks(fig, left_in, bottom_in, w_in, h_in, tick=0.10, lw=0.4):
    def fi(x): return x / A4_W
    def fj(y): return y / A4_H
    kw = dict(color='#aaa', lw=lw, transform=fig.transFigure, clip_on=False)
    for cx, dx in [(left_in, -tick), (left_in + w_in, tick)]:
        for cy, dy in [(bottom_in, -tick), (bottom_in + h_in, tick)]:
            fig.add_artist(plt.Line2D([fi(cx), fi(cx)], [fj(cy + dy), fj(cy)], **kw))
            fig.add_artist(plt.Line2D([fi(cx + dx), fi(cx)], [fj(cy), fj(cy)], **kw))

PDF_DPI = 150

# ── frentes de cartas objetivo ────────────────────────────────────────────────
with PdfPages('deck_a4_fronts_es.pdf') as pdf:
    for page in range(n_pages):
        fig = plt.figure(figsize=(A4_W, A4_H), facecolor='white')
        page_cards = CARDS[page * PER_PAGE : (page + 1) * PER_PAGE]

        fig.text(0.5, (A4_H - MARGIN_Y * 0.6) / A4_H,
                 f"CIRCUIT MASTER  ·  Frentes de Cartas  (página {page + 1} de {n_pages})",
                 ha='center', va='top', fontsize=9, color='#444',
                 transform=fig.transFigure)

        for i, card in enumerate(page_cards):
            row = i // COLS_PAGE
            col = i % COLS_PAGE
            left_in   = MARGIN_X + col * (CARD_W + GAP_X)
            bottom_in = MARGIN_Y + (ROWS_PAGE - 1 - row) * (CARD_H + GAP_Y)
            ax = fig.add_axes([left_in / A4_W, bottom_in / A4_H,
                               CARD_W / A4_W,  CARD_H / A4_H])
            draw_deck_card(ax, **card)
            _add_crop_marks(fig, left_in, bottom_in, CARD_W, CARD_H)

        pdf.savefig(fig, dpi=PDF_DPI)
        plt.close(fig)

print(f"Guardado: deck_a4_fronts_es.pdf  ({n_pages} páginas)")

# ── reversos de cartas objetivo ───────────────────────────────────────────────
with PdfPages('deck_a4_backs_es.pdf') as pdf:
    for page in range(n_pages):
        fig = plt.figure(figsize=(A4_W, A4_H), facecolor='white')
        n_this = min(PER_PAGE, len(CARDS) - page * PER_PAGE)

        fig.text(0.5, (A4_H - MARGIN_Y * 0.6) / A4_H,
                 f"CIRCUIT MASTER  ·  Reversos de Cartas  (página {page + 1} de {n_pages})"
                 "  — imprimir al reverso",
                 ha='center', va='top', fontsize=9, color='#444',
                 transform=fig.transFigure)

        for i in range(n_this):
            row = i // COLS_PAGE
            col = (COLS_PAGE - 1) - (i % COLS_PAGE)
            left_in   = MARGIN_X + col * (CARD_W + GAP_X)
            bottom_in = MARGIN_Y + (ROWS_PAGE - 1 - row) * (CARD_H + GAP_Y)
            ax = fig.add_axes([left_in / A4_W, bottom_in / A4_H,
                               CARD_W / A4_W,  CARD_H / A4_H])
            draw_card_back(ax)
            _add_crop_marks(fig, left_in, bottom_in, CARD_W, CARD_H)

        pdf.savefig(fig, dpi=PDF_DPI)
        plt.close(fig)

print(f"Guardado: deck_a4_backs_es.pdf   ({n_pages} páginas)")

# ── vista general PNG ─────────────────────────────────────────────────────────
N_COLS = 8
N_ROWS = 4
MARGIN = 0.35
GAP    = 0.12

fig_w = N_COLS * CARD_W + (N_COLS - 1) * GAP + 2 * MARGIN
fig_h = N_ROWS * CARD_H + (N_ROWS - 1) * GAP + 2 * MARGIN + 0.5

fig = plt.figure(figsize=(fig_w, fig_h), facecolor='#eeeeee')
fig.text(0.5, 1 - 0.18 / fig_h,
         "CIRCUIT MASTER  ·  Mazo de Cartas Objetivo",
         ha='center', va='top', fontsize=13, fontweight='bold', color='#222',
         transform=fig.transFigure)

for idx, card in enumerate(CARDS):
    row = idx // N_COLS
    col = idx % N_COLS
    left   = (MARGIN + col * (CARD_W + GAP)) / fig_w
    bottom = (fig_h - MARGIN - 0.5 - (row + 1) * CARD_H - row * GAP) / fig_h
    ax = fig.add_axes([left, bottom, CARD_W / fig_w, CARD_H / fig_h])
    draw_deck_card(ax, **card)

fig.savefig('deck_objective_cards_es.png', dpi=200, bbox_inches='tight', facecolor='#eeeeee')
plt.close(fig)
print(f"Guardado: deck_objective_cards_es.png  ({N_COLS}×{N_ROWS} vista general)")

# ── PDF interleaved de objetivos ──────────────────────────────────────────────
from pypdf import PdfReader, PdfWriter

def _interleave_pdfs(fronts_path, backs_path, out_path):
    fronts = PdfReader(fronts_path)
    backs  = PdfReader(backs_path)
    writer = PdfWriter()
    for i in range(len(fronts.pages)):
        writer.add_page(fronts.pages[i])
        writer.add_page(backs.pages[i])
    with open(out_path, 'wb') as f:
        writer.write(f)
    return len(fronts.pages) * 2

n = _interleave_pdfs('deck_a4_fronts_es.pdf', 'deck_a4_backs_es.pdf', 'deck_a4_print_es.pdf')
print(f"Guardado: deck_a4_print_es.pdf  ({n} páginas, frente/reverso intercalados)")

# ═══════════════════════════════════════════════════════════════════════════════
# CARTAS DE COMPONENTES
# ═══════════════════════════════════════════════════════════════════════════════

_COMPONENT_TYPES = [
    dict(card_type='resistor',  value=100, unit='Ω',  color='#e65100', count=40, label='RESISTOR'),
    dict(card_type='resistor',  value=200, unit='Ω',  color='#6a1b9a', count=20, label='RESISTOR'),
    dict(card_type='resistor',  value=300, unit='Ω',  color='#1565c0', count=20, label='RESISTOR'),
    dict(card_type='capacitor', value=10,  unit='µF', color='#00695c', count=40, label='CAPACITOR'),
    dict(card_type='capacitor', value=20,  unit='µF', color='#0277bd', count=20, label='CAPACITOR'),
    dict(card_type='capacitor', value=30,  unit='µF', color='#283593', count=20, label='CAPACITOR'),
]
COMPONENT_CARDS = [card for card in _COMPONENT_TYPES for _ in range(card['count'])]

def _draw_wire_symbol(ax, xc, yc, color, lw=3):
    theta = np.linspace(0, np.pi, 200)
    r = 3.2
    xs = xc + r * np.cos(np.pi - theta)
    ys = yc + r * 0.45 * np.sin(theta)
    ax.plot(xs, ys, color=color, lw=lw, solid_capstyle='round', zorder=4)
    for xp in [xc - r, xc + r]:
        ax.plot([xp, xp], [yc - 0.35, yc], color=color, lw=lw * 0.9,
                solid_capstyle='round', zorder=4)
        ax.plot(xp, yc - 0.35, 'o', color=color, markersize=7, zorder=5)

def draw_component_card(ax, card_type, value, unit, color, count, label):
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 14)
    ax.axis('off')

    ax.add_patch(plt.Rectangle((0, 0), 10, 14, facecolor='white', edgecolor='none', zorder=1))
    ax.add_patch(plt.Rectangle((0.12, 0.12), 9.76, 13.76,
                               fill=False, edgecolor=color, lw=2.2, zorder=6))

    ax.add_patch(plt.Rectangle((0, 11.6), 10, 2.4, facecolor=color, edgecolor='none', zorder=2))
    ax.text(5, 12.8, label, ha='center', va='center',
            fontsize=11, fontweight='bold', color='white', zorder=3)

    ax.add_patch(plt.Circle((1.15, 12.8), 0.65,
                            facecolor='white', edgecolor='none', zorder=4))
    ax.text(1.15, 12.8, '1 AP', ha='center', va='center',
            fontsize=6.5, fontweight='bold', color=color, zorder=5)

    sym_yc   = 8.2
    sym_yspan = 3.5

    if card_type == 'wire':
        _draw_wire_symbol(ax, xc=5.0, yc=sym_yc, color=color, lw=3.5)
    else:
        topo = ('R', value) if card_type == 'resistor' else ('C', value)
        _draw_element(ax, topo, x0=1.5, x1=8.5, yc=sym_yc, yspan=sym_yspan,
                      lw=3.0, fsize=0, color=color)

    if card_type == 'wire':
        val_text = 'CABLE PUENTE'
        val_size = 13
    else:
        val_text = f'{value} {unit}'
        val_size = 20
    ax.text(5, 5.5, val_text, ha='center', va='center',
            fontsize=val_size, fontweight='bold', color=color, zorder=4)

    rules = {
        'wire':      'Conecta columnas adyacentes\nen la misma fila',
        'resistor':  'Coloca entre dos filas\nadyacentes en la misma columna',
        'capacitor': 'Coloca entre dos filas\nadyacentes en la misma columna',
    }
    ax.text(5, 3.9, rules[card_type], ha='center', va='center',
            fontsize=8, color='#555', zorder=4, multialignment='center')

    ax.add_patch(plt.Rectangle((3.2, 1.0), 3.6, 1.1,
                               facecolor=color, edgecolor='none', alpha=0.12,
                               zorder=3, clip_on=False))
    ax.text(5, 1.55, f'×{count} en el mazo', ha='center', va='center',
            fontsize=8.5, color=color, fontweight='bold', zorder=4)

# ── frentes de componentes ────────────────────────────────────────────────────
with PdfPages('components_a4_fronts_es.pdf') as pdf:
    n_comp    = len(COMPONENT_CARDS)
    n_pages_c = (n_comp + PER_PAGE - 1) // PER_PAGE
    for page in range(n_pages_c):
        page_cards = COMPONENT_CARDS[page * PER_PAGE:(page + 1) * PER_PAGE]
        fig = plt.figure(figsize=(A4_W, A4_H), facecolor='white')
        fig.text(0.5, (A4_H - MARGIN_Y * 0.6) / A4_H,
                 f"CIRCUIT MASTER  ·  Cartas de Componentes  (página {page + 1} de {n_pages_c})",
                 ha='center', va='top', fontsize=9, color='#444',
                 transform=fig.transFigure)
        for i, card in enumerate(page_cards):
            row = i // COLS_PAGE
            col = i % COLS_PAGE
            left_in   = MARGIN_X + col * (CARD_W + GAP_X)
            bottom_in = MARGIN_Y + (ROWS_PAGE - 1 - row) * (CARD_H + GAP_Y)
            ax = fig.add_axes([left_in / A4_W, bottom_in / A4_H,
                               CARD_W / A4_W,  CARD_H / A4_H])
            draw_component_card(ax, **card)
            _add_crop_marks(fig, left_in, bottom_in, CARD_W, CARD_H)
        pdf.savefig(fig, dpi=PDF_DPI)
        plt.close(fig)

print(f"Guardado: components_a4_fronts_es.pdf  ({n_pages_c} páginas)")

# ── reversos de componentes ───────────────────────────────────────────────────
with PdfPages('components_a4_backs_es.pdf') as pdf:
    for page in range(n_pages_c):
        n_this = min(PER_PAGE, n_comp - page * PER_PAGE)
        fig = plt.figure(figsize=(A4_W, A4_H), facecolor='white')
        fig.text(0.5, (A4_H - MARGIN_Y * 0.6) / A4_H,
                 f"CIRCUIT MASTER  ·  Reversos de Componentes  (página {page + 1} de {n_pages_c})"
                 "  — imprimir al reverso",
                 ha='center', va='top', fontsize=9, color='#444',
                 transform=fig.transFigure)
        for i in range(n_this):
            row = i // COLS_PAGE
            col = (COLS_PAGE - 1) - (i % COLS_PAGE)
            left_in   = MARGIN_X + col * (CARD_W + GAP_X)
            bottom_in = MARGIN_Y + (ROWS_PAGE - 1 - row) * (CARD_H + GAP_Y)
            ax = fig.add_axes([left_in / A4_W, bottom_in / A4_H,
                               CARD_W / A4_W,  CARD_H / A4_H])
            draw_component_back(ax)
            _add_crop_marks(fig, left_in, bottom_in, CARD_W, CARD_H)
        pdf.savefig(fig, dpi=PDF_DPI)
        plt.close(fig)

print(f"Guardado: components_a4_backs_es.pdf   ({n_pages_c} páginas)")

# ── PDF interleaved de componentes ────────────────────────────────────────────
n = _interleave_pdfs('components_a4_fronts_es.pdf', 'components_a4_backs_es.pdf',
                     'components_a4_print_es.pdf')
print(f"Guardado: components_a4_print_es.pdf  ({n} páginas, frente/reverso intercalados)")
