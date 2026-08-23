"""
Generate individual PNG files for every unique card face (front only).
Output folder: card_images/
  card_images/objective_*.png   — 32 objective cards
  card_images/component_*.png   — 6 component types

Each PNG is 2.5" × 3.5" at 200 DPI (500 × 700 px).
Self-contained: imports only from generate_plots (no side-effects).
"""
import os
import re
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import numpy as np

from generate_plots import _TOPOLOGIES, _max_parallel_branches, _draw_element

OUT_DIR = 'card_images'
CARD_W  = 2.5    # inches
CARD_H  = 3.5    # inches
PNG_DPI = 200    # → 500 × 700 px

LOGO_PATH = os.path.join(os.path.dirname(__file__),
                         'Gemini_Generated_Image_lno85mlno85mlno8.png')

os.makedirs(OUT_DIR, exist_ok=True)


# ── card data ─────────────────────────────────────────────────────────────────

OBJECTIVE_CARDS = [
    # 2-component resistance — SETUP tier
    dict(route_desc="Series 200Ω",    target_req=200,    points=30, obj_type="resistance", n=2),
    dict(route_desc="Parallel 50Ω",   target_req=50,     points=30, obj_type="resistance", n=2),
    dict(route_desc="Series 300Ω",    target_req=300,    points=30, obj_type="resistance", n=2),
    dict(route_desc="Parallel 67Ω",   target_req=66.67,  points=30, obj_type="resistance", n=2),
    dict(route_desc="Series 400Ω",    target_req=400,    points=35, obj_type="resistance", n=2),
    dict(route_desc="Parallel 75Ω",   target_req=75,     points=30, obj_type="resistance", n=2),
    dict(route_desc="Series 500Ω",    target_req=500,    points=40, obj_type="resistance", n=2),
    dict(route_desc="Parallel 120Ω",  target_req=120,    points=35, obj_type="resistance", n=2),
    # 3-component resistance — BUILD tier
    dict(route_desc="3-Parallel 33Ω", target_req=33.33,  points=40, obj_type="resistance", n=3),
    dict(route_desc="Mixed 250Ω",     target_req=250,    points=45, obj_type="resistance", n=3),
    dict(route_desc="Mixed 350Ω",     target_req=350,    points=45, obj_type="resistance", n=3),
    dict(route_desc="Mixed 167Ω",     target_req=166.67, points=45, obj_type="resistance", n=3),
    dict(route_desc="Mixed 175Ω",     target_req=175,    points=45, obj_type="resistance", n=3),
    dict(route_desc="Mixed 220Ω",     target_req=220,    points=45, obj_type="resistance", n=3),
    # 4-component resistance — EXPERT tier
    dict(route_desc="Bridge 100Ω",    target_req=100,    points=65, obj_type="resistance", n=4),
    dict(route_desc="Mixed 133Ω",     target_req=133.33, points=65, obj_type="resistance", n=4),
    # 2-component capacitance — SETUP tier
    dict(route_desc="Series 5µF",      target_req=5,     points=30, obj_type="capacitance", n=2),
    dict(route_desc="Series 6.7µF",    target_req=6.67,  points=30, obj_type="capacitance", n=2),
    dict(route_desc="Series 7.5µF",    target_req=7.5,   points=30, obj_type="capacitance", n=2),
    dict(route_desc="Series 12µF",     target_req=12,    points=35, obj_type="capacitance", n=2),
    dict(route_desc="Series 10µF",     target_req=10,    points=30, obj_type="capacitance", n=2),
    dict(route_desc="Parallel 20µF",   target_req=20,    points=30, obj_type="capacitance", n=2),
    dict(route_desc="Parallel 40µF",   target_req=40,    points=35, obj_type="capacitance", n=2),
    dict(route_desc="Parallel 50µF",   target_req=50,    points=35, obj_type="capacitance", n=2),
    # 3-component capacitance — BUILD tier
    dict(route_desc="Series 3.3µF",    target_req=3.33,  points=35, obj_type="capacitance", n=3),
    dict(route_desc="Series 4µF",      target_req=4,     points=40, obj_type="capacitance", n=3),
    dict(route_desc="Series 6µF",      target_req=6,     points=40, obj_type="capacitance", n=3),
    dict(route_desc="Mixed 8µF",       target_req=8,     points=45, obj_type="capacitance", n=3),
    dict(route_desc="Mixed 13.3µF",    target_req=13.33, points=45, obj_type="capacitance", n=3),
    dict(route_desc="3-Parallel 60µF", target_req=60,    points=45, obj_type="capacitance", n=3),
    # 4-component capacitance — EXPERT tier
    dict(route_desc="Series 2.5µF",    target_req=2.5,   points=65, obj_type="capacitance", n=4),
    dict(route_desc="Series 3µF",      target_req=3,     points=65, obj_type="capacitance", n=4),
]

COMPONENT_TYPES = [
    dict(card_type='resistor',  value=100, unit='Ω',  color='#e65100', count=40, label='RESISTOR'),
    dict(card_type='resistor',  value=200, unit='Ω',  color='#6a1b9a', count=20, label='RESISTOR'),
    dict(card_type='resistor',  value=300, unit='Ω',  color='#1565c0', count=20, label='RESISTOR'),
    dict(card_type='capacitor', value=10,  unit='µF', color='#00695c', count=40, label='CAPACITOR'),
    dict(card_type='capacitor', value=20,  unit='µF', color='#0277bd', count=20, label='CAPACITOR'),
    dict(card_type='capacitor', value=30,  unit='µF', color='#283593', count=20, label='CAPACITOR'),
]


# ── drawing helpers ───────────────────────────────────────────────────────────

def _tier(obj_type, n):
    if n == 4:
        tier = "EXPERT"
    elif n == 3:
        tier = "BUILD"
    else:
        tier = "SETUP"
    if obj_type == "capacitance":
        color = {'SETUP': '#0288d1', 'BUILD': '#00838f', 'EXPERT': '#1a237e'}[tier]
        return tier, color
    return tier, {'EXPERT': '#6a1b9a', 'BUILD': '#e65100', 'SETUP': '#2e7d32'}[tier]


def draw_objective_card(ax, route_desc, target_req, points, obj_type="resistance", n=2):
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 14)
    ax.axis('off')

    tier_label, color = _tier(obj_type, n)
    unit = "µF" if obj_type == "capacitance" else "Ω"

    ax.add_patch(plt.Rectangle((0, 0), 10, 14,
                               facecolor='white', edgecolor=color, lw=2.0, zorder=1))
    ax.add_patch(plt.Rectangle((0, 11.2), 10, 2.8,
                               facecolor=color, edgecolor='none', zorder=2))

    ax.text(1.2, 12.75, "=",
            ha='left', va='center', fontsize=13, fontweight='bold',
            color='white', alpha=0.7, zorder=3)
    ax.plot([2.0, 8.3], [12.55, 12.55], color='white', lw=1.5, alpha=0.7, zorder=3)
    ax.text(8.7, 12.75, unit,
            ha='left', va='center', fontsize=11, fontweight='bold',
            color='white', alpha=0.7, zorder=3)
    ax.text(0.4, 13.6, tier_label,
            ha='left', va='top', fontsize=7, fontweight='bold',
            color='white', alpha=0.85, zorder=3)
    ax.text(9.6, 13.6, f"×{n}",
            ha='right', va='top', fontsize=7, fontweight='bold',
            color='white', alpha=0.85, zorder=3)

    topo = _TOPOLOGIES.get(route_desc)
    if topo:
        max_n = _max_parallel_branches(topo)
        yspan = min(7.0, max(3.0, max_n * 2.1))
        _draw_element(ax, topo, 0.7, 9.3, 6.8, yspan, lw=1.8, fsize=8.0, color='#1a1a1a')
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

    icon_lw, icon_y, spacing, x_start = 1.4, 1.4, 1.5, 0.9
    for i in range(n):
        ix = x_start + i * spacing
        if obj_type == "resistance":
            h, dz = 0.28, 0.10
            zx = [ix + j * dz for j in range(7)]
            zy = [icon_y, icon_y+h, icon_y-h, icon_y+h, icon_y-h, icon_y+h, icon_y]
            ax.plot(zx, zy, color=color, lw=icon_lw,
                    solid_capstyle='round', solid_joinstyle='round', zorder=3)
        else:
            mid, gap, cap_h = ix + 0.3, 0.07, 0.38
            ax.plot([ix, mid-gap], [icon_y, icon_y], color=color, lw=icon_lw, zorder=3)
            ax.plot([mid+gap, ix+0.6], [icon_y, icon_y], color=color, lw=icon_lw, zorder=3)
            ax.plot([mid-gap, mid-gap], [icon_y-cap_h/2, icon_y+cap_h/2],
                    color=color, lw=icon_lw*2, solid_capstyle='butt', zorder=3)
            ax.plot([mid+gap, mid+gap], [icon_y-cap_h/2, icon_y+cap_h/2],
                    color=color, lw=icon_lw*2, solid_capstyle='butt', zorder=3)


def draw_component_card(ax, card_type, value, unit, color, count, label):
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 14)
    ax.axis('off')

    ax.add_patch(plt.Rectangle((0, 0), 10, 14,
                               facecolor='white', edgecolor='none', zorder=1))
    ax.add_patch(plt.Rectangle((0.12, 0.12), 9.76, 13.76,
                               fill=False, edgecolor=color, lw=2.2, zorder=6))
    ax.add_patch(plt.Rectangle((0, 11.6), 10, 2.4,
                               facecolor=color, edgecolor='none', zorder=2))
    ax.text(5, 12.8, label, ha='center', va='center',
            fontsize=11, fontweight='bold', color='white', zorder=3)

    ax.add_patch(plt.Circle((1.15, 12.8), 0.65,
                            facecolor='white', edgecolor='none', zorder=4))
    ax.text(1.15, 12.8, '1 AP', ha='center', va='center',
            fontsize=6.5, fontweight='bold', color=color, zorder=5)

    topo = ('R', value) if card_type == 'resistor' else ('C', value)
    _draw_element(ax, topo, x0=1.5, x1=8.5, yc=8.2, yspan=3.5,
                  lw=3.0, fsize=0, color=color)

    ax.text(5, 5.5, f'{value} {unit}', ha='center', va='center',
            fontsize=20, fontweight='bold', color=color, zorder=4)

    rule = 'In your zone: same column,\ntwo adjacent rows (vertical)'
    ax.text(5, 3.9, rule, ha='center', va='center',
            fontsize=8, color='#555', zorder=4, multialignment='center')

    ax.add_patch(plt.Rectangle((3.2, 1.0), 3.6, 1.1,
                               facecolor=color, edgecolor='none', alpha=0.12,
                               zorder=3, clip_on=False))
    ax.text(5, 1.55, f'×{count} in deck', ha='center', va='center',
            fontsize=8.5, color=color, fontweight='bold', zorder=4)


# ── filename helper ───────────────────────────────────────────────────────────

def _slug(text):
    text = text.replace('Ω', 'ohm').replace('µF', 'uf').replace('µ', 'u')
    text = text.replace(' ', '_').replace('-', '_').replace('.', 'p')
    return re.sub(r'[^a-zA-Z0-9_]', '', text).lower()


def save_card(draw_fn, kwargs, filename):
    fig = plt.figure(figsize=(CARD_W, CARD_H), facecolor='white')
    ax  = fig.add_axes([0, 0, 1, 1])
    draw_fn(ax, **kwargs)
    path = os.path.join(OUT_DIR, filename)
    fig.savefig(path, dpi=PNG_DPI, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return path


# ── main ─────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print(f"Saving to '{OUT_DIR}/'  ({PNG_DPI} DPI, {int(CARD_W*PNG_DPI)}×{int(CARD_H*PNG_DPI)} px)\n")

    print("Objective cards:")
    for card in OBJECTIVE_CARDS:
        slug = _slug(card['route_desc'])
        path = save_card(draw_objective_card, card, f"objective_{slug}.png")
        print(f"  {os.path.basename(path)}")

    print("\nComponent cards:")
    for comp in COMPONENT_TYPES:
        slug = _slug(f"{comp['card_type']}_{comp['value']}{comp['unit']}")
        path = save_card(draw_component_card, comp, f"component_{slug}.png")
        print(f"  {os.path.basename(path)}")

    total = len(OBJECTIVE_CARDS) + len(COMPONENT_TYPES)
    print(f"\nDone — {total} PNGs saved to '{OUT_DIR}/'")
