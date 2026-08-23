"""
Generate a printable Circuit Master game board (A4 portrait) — Spanish version.
Output: board_a4_es.pdf, board_a4_es.png
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.image as mpimg
import numpy as np
import os
from matplotlib.backends.backend_pdf import PdfPages

LOGO_PATH = os.path.join(os.path.dirname(__file__),
                         'Gemini_Generated_Image_lno85mlno85mlno8.png')

# ── palette ───────────────────────────────────────────────────────────────────
TEAL      = '#0d7f7a'
NAVY      = '#263238'
P1_BG     = '#e3f2fd'
P1_DARK   = '#1565c0'
P1_HOLE   = '#90caf9'
P2_BG     = '#fff3e0'
P2_DARK   = '#e65100'
P2_HOLE   = '#ffcc80'
NEU_BG    = '#eeeeee'
NEU_HOLE  = '#bdbdbd'
RAIL_POS  = '#c62828'
RAIL_NEG  = '#37474f'
BOARD_BG  = '#fafaf6'

A4_W, A4_H = 8.27, 11.69

fig = plt.figure(figsize=(A4_W, A4_H), facecolor='white', dpi=150)
ax  = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, A4_W)
ax.set_ylim(0, A4_H)
ax.axis('off')

# ── rounded rectangle helper ──────────────────────────────────────────────────
def rrect(x, y, w, h, r=0.06, fc='white', ec='gray', lw=1, alpha=1, zorder=2):
    r = min(r, w/2, h/2)
    p = patches.FancyBboxPatch(
        (x + r, y + r), max(1e-3, w - 2*r), max(1e-3, h - 2*r),
        boxstyle=f'round,pad={r}',
        facecolor=fc, edgecolor=ec, linewidth=lw, alpha=alpha,
        zorder=zorder, clip_on=False)
    ax.add_patch(p)

# ── layout (portrait A4, bottom→top) ─────────────────────────────────────────
MAR     = 0.25
GAP     = 0.08
SCORE_H = 3.16
BOARD_H = 7.00
HDR_H   = 0.87

SCORE_Y0 = MAR
BOARD_Y0 = SCORE_Y0 + SCORE_H + GAP
HDR_Y0   = BOARD_Y0 + BOARD_H + GAP

CX0 = MAR
CW  = A4_W - 2 * MAR   # 7.77"

# ═════════════════════════════════════════════════════════════════════════════
# ENCABEZADO
# ═════════════════════════════════════════════════════════════════════════════
ax.add_patch(patches.Rectangle((0, HDR_Y0), A4_W, HDR_H + 0.25,
                               facecolor='white', edgecolor='none', zorder=1))
ax.plot([0, A4_W], [HDR_Y0, HDR_Y0], color=TEAL, lw=1.5, zorder=2)

# ── logo ──────────────────────────────────────────────────────────────────────
LOGO_H = HDR_H * 0.92
LOGO_W = LOGO_H * 1.5
LOGO_X = CX0 + 0.05
LOGO_Y = HDR_Y0 + (HDR_H - LOGO_H) / 2
if os.path.exists(LOGO_PATH):
    logo_img = mpimg.imread(LOGO_PATH)
    ax.imshow(logo_img, extent=[LOGO_X, LOGO_X + LOGO_W, LOGO_Y, LOGO_Y + LOGO_H],
              aspect='auto', zorder=4)

# ── título ────────────────────────────────────────────────────────────────────
tx = LOGO_X + LOGO_W + 0.15
ax.text(tx, HDR_Y0 + HDR_H * 0.63, 'CIRCUIT MASTER',
        ha='left', va='center', fontsize=16, fontweight='bold', color=TEAL, zorder=3)
ax.text(tx, HDR_Y0 + HDR_H * 0.22, 'Un Juego Educativo de Electrónica',
        ha='left', va='center', fontsize=7.5, color=NAVY, alpha=0.75, zorder=3)

# ── campos de hora / fecha ────────────────────────────────────────────────────
for label, x, line_w in [('Inicio:', 4.2, 0.80), ('Fin:', 5.6, 0.85), ('Fecha:', 7.0, 0.70)]:
    ax.text(x, HDR_Y0 + HDR_H * 0.63, label,
            ha='left', va='center', fontsize=8, color=NAVY, fontweight='bold', zorder=3)
    lx = x + 0.55
    ax.plot([lx, lx + line_w], [HDR_Y0 + HDR_H * 0.38, HDR_Y0 + HDR_H * 0.38],
            color=NAVY, lw=0.9, alpha=0.4, zorder=3)

# ═════════════════════════════════════════════════════════════════════════════
# PROTOBOARD
# ═════════════════════════════════════════════════════════════════════════════
N_COLS, N_ROWS = 14, 15
PAD_X = 0.52
PAD_Y = 0.38
AW = CW - 2 * PAD_X
AH = BOARD_H - 2 * PAD_Y
CS = AW / (N_COLS - 1)
RS = AH / (N_ROWS - 1)

rrect(CX0, BOARD_Y0, CW, BOARD_H, r=0.10, fc=BOARD_BG, ec=NAVY, lw=1.8, zorder=2)

def hxy(col, row):
    return (CX0 + PAD_X + col * CS,
            BOARD_Y0 + PAD_Y + (N_ROWS - 1 - row) * RS)

# ── ranura central ────────────────────────────────────────────────────────────
rx0 = hxy(6, 0)[0] + CS * 0.42
rx1 = hxy(7, 0)[0] - CS * 0.42
ry0 = BOARD_Y0 + PAD_Y * 0.25
rh  = BOARD_H  - PAD_Y * 0.50
ax.add_patch(patches.Rectangle((rx0, ry0), rx1 - rx0, rh,
                               facecolor='#dde3e8', edgecolor='#b0bec5', lw=0.5, zorder=3))
ax.text((rx0 + rx1) / 2, BOARD_Y0 + BOARD_H / 2, 'RANURA',
        ha='center', va='center', fontsize=4.5, color='#90a4ae', rotation=90, zorder=5)

# ── sombreado de rieles de alimentación ───────────────────────────────────────
for col, color in [(0, RAIL_POS), (1, RAIL_NEG), (12, RAIL_POS), (13, RAIL_NEG)]:
    x = hxy(col, 0)[0]
    ax.add_patch(patches.Rectangle((x - CS * 0.4, ry0), CS * 0.8, rh,
                                   facecolor=color, edgecolor='none', alpha=0.10, zorder=3))

# ── orificios ─────────────────────────────────────────────────────────────────
HR = 0.055
for row in range(N_ROWS):
    for col in range(N_COLS):
        x, y = hxy(col, row)
        if   col in (0, 12):  fc, ec = RAIL_POS, '#8b0000'
        elif col in (1, 13):  fc, ec = RAIL_NEG, '#111'
        else:                 fc, ec = NEU_HOLE, '#757575'
        ax.add_patch(plt.Circle((x, y), HR,        fc=fc, ec=ec, lw=0.6, zorder=5))
        ax.add_patch(plt.Circle((x, y), HR * 0.42, fc='white', ec='none', zorder=6))

# ── etiquetas de columna (A–J, +/−) ──────────────────────────────────────────
col_names = {2:'A',3:'B',4:'C',5:'D',6:'E',7:'F',8:'G',9:'H',10:'I',11:'J'}
top_y = BOARD_Y0 + BOARD_H - PAD_Y * 0.44
bot_y = BOARD_Y0            + PAD_Y * 0.44

for col, name in col_names.items():
    x = hxy(col, 0)[0]
    for y in (top_y, bot_y):
        ax.text(x, y, name, ha='center', va='center',
                fontsize=7.5, fontweight='bold', color=NAVY, zorder=7)

for col, sym in [(0,'+'),(1,'−'),(12,'+'),(13,'−')]:
    c = RAIL_POS if sym == '+' else RAIL_NEG
    x = hxy(col, 0)[0]
    for y in (top_y, bot_y):
        ax.text(x, y, sym, ha='center', va='center',
                fontsize=9, fontweight='bold', color=c, zorder=7)

# ── números de fila (lado derecho) ────────────────────────────────────────────
for row in range(N_ROWS):
    _, y = hxy(0, row)
    ax.text(CX0 + CW - 0.17, y, str(row),
            ha='center', va='center', fontsize=6, color='#607d8b', zorder=7)

# ═════════════════════════════════════════════════════════════════════════════
# TABLA DE PUNTUACIÓN
# ═════════════════════════════════════════════════════════════════════════════
rrect(CX0, SCORE_Y0, CW, SCORE_H, r=0.08, fc='#f9f9f9', ec=NAVY, lw=1.2, zorder=2)
ax.text(CX0 + CW/2, SCORE_Y0 + SCORE_H - 0.13,
        'TABLA DE PUNTUACIÓN', ha='center', va='center',
        fontsize=8.5, fontweight='bold', color=NAVY, zorder=4)

TX0 = CX0 + 0.13
TW  = CW  - 0.26
TY0 = SCORE_Y0 + 0.13
TH  = SCORE_H  - 0.31

# ── Marcador horizontal: jugadores como filas, turnos como columnas ───────────
NAME_W  = 1.10
TOTAL_W = 0.82
TURN_W  = (TW - NAME_W - TOTAL_W) / 6

HDR_H_ROW = 0.36
PLAYER_H  = (TH - HDR_H_ROW) / 2

def col_x(i):   # i=0..7: 0=nombre, 1-6=turnos, 7=total
    if i == 0: return TX0
    if i == 7: return TX0 + NAME_W + 6 * TURN_W
    return TX0 + NAME_W + (i - 1) * TURN_W

# ── encabezado de columnas ────────────────────────────────────────────────────
hdr_y = TY0 + TH - HDR_H_ROW
# celda de nombre
ax.add_patch(patches.Rectangle((col_x(0), hdr_y), NAME_W, HDR_H_ROW,
                               facecolor=NAVY, edgecolor='none', zorder=3))
# turnos de preparación (1-2) — tono azul
ax.add_patch(patches.Rectangle((col_x(1), hdr_y), TURN_W * 2, HDR_H_ROW,
                               facecolor=P1_DARK, edgecolor='none', alpha=0.85, zorder=3))
ax.text(col_x(1) + TURN_W, hdr_y + HDR_H_ROW * 0.72, 'PREPARACIÓN',
        ha='center', va='center', fontsize=5.5, fontweight='bold', color='white', zorder=4)
# turnos de construcción (3-6) — tono naranja
ax.add_patch(patches.Rectangle((col_x(3), hdr_y), TURN_W * 4, HDR_H_ROW,
                               facecolor=P2_DARK, edgecolor='none', alpha=0.85, zorder=3))
ax.text(col_x(3) + TURN_W * 2, hdr_y + HDR_H_ROW * 0.72, 'CONSTRUCCIÓN',
        ha='center', va='center', fontsize=5.5, fontweight='bold', color='white', zorder=4)
# celda de total
ax.add_patch(patches.Rectangle((col_x(7), hdr_y), TOTAL_W, HDR_H_ROW,
                               facecolor=NAVY, edgecolor='none', zorder=3))
ax.text(col_x(7) + TOTAL_W/2, hdr_y + HDR_H_ROW/2, 'TOTAL',
        ha='center', va='center', fontsize=7, fontweight='bold', color='white', zorder=4)
# números de turno
for t in range(1, 7):
    cx2 = col_x(t)
    ax.text(cx2 + TURN_W/2, hdr_y + HDR_H_ROW * 0.28, str(t),
            ha='center', va='center', fontsize=8, fontweight='bold', color='white', zorder=4)

# ── filas de jugadores ────────────────────────────────────────────────────────
for pi, (pid, bg, dark) in enumerate([(1, P1_BG, P1_DARK), (2, P2_BG, P2_DARK)]):
    ry = TY0 + TH - HDR_H_ROW - (pi + 1) * PLAYER_H

    # celda de nombre
    ax.add_patch(patches.Rectangle((col_x(0), ry), NAME_W, PLAYER_H,
                                   facecolor=dark, edgecolor='none', zorder=3))
    ax.text(col_x(0) + NAME_W/2, ry + PLAYER_H/2, f'EQUIPO {pid}',
            ha='center', va='center', fontsize=9, fontweight='bold',
            color='white', zorder=4, rotation=0)

    # celdas de puntuación por turno
    for t in range(1, 7):
        cx2 = col_x(t)
        cell_bg = '#f0f6ff' if t <= 2 else '#fff8f0'
        ax.add_patch(patches.Rectangle((cx2, ry), TURN_W, PLAYER_H,
                                       facecolor=cell_bg, edgecolor='none', zorder=3))
        ax.plot([cx2 + TURN_W*0.15, cx2 + TURN_W*0.85],
                [ry + PLAYER_H * 0.38, ry + PLAYER_H * 0.38],
                color='#ccc', lw=0.7, zorder=4)

    # celda de total
    ax.add_patch(patches.Rectangle((col_x(7), ry), TOTAL_W, PLAYER_H,
                                   facecolor=bg, edgecolor='none', zorder=3))
    ax.plot([col_x(7) + TOTAL_W*0.15, col_x(7) + TOTAL_W*0.85],
            [ry + PLAYER_H * 0.38, ry + PLAYER_H * 0.38],
            color=dark, lw=0.8, alpha=0.4, zorder=4)

# ── divisor horizontal entre filas de jugadores ───────────────────────────────
mid_y = TY0 + TH - HDR_H_ROW - PLAYER_H
ax.plot([TX0, TX0 + TW], [mid_y, mid_y], color=NAVY, lw=1.5, zorder=5)

# ── divisores verticales ──────────────────────────────────────────────────────
for i in range(1, 8):
    lw = 1.2 if i in (1, 3, 7) else 0.4
    ax.plot([col_x(i), col_x(i)], [TY0, TY0 + TH],
            color=NAVY, lw=lw, alpha=(1.0 if lw > 0.5 else 0.35), zorder=4)

ax.add_patch(patches.Rectangle((TX0, TY0), TW, TH,
                               fill=False, ec=NAVY, lw=0.9, zorder=5))

# ═════════════════════════════════════════════════════════════════════════════
# SALIDA
# ═════════════════════════════════════════════════════════════════════════════
with PdfPages('board_a4_es.pdf') as pdf:
    pdf.savefig(fig, dpi=150)

fig.savefig('board_a4_es.png', dpi=150, bbox_inches='tight')
plt.close(fig)
print("Guardado: board_a4_es.pdf y board_a4_es.png")
