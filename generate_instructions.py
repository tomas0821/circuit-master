"""
Generate printable instruction booklets for Circuit Master (A4, 4 pages each).
Output: instructions_en.pdf, instructions_es.pdf
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.image as mpimg
import os
from matplotlib.backends.backend_pdf import PdfPages

LOGO_PATH = os.path.join(os.path.dirname(__file__),
                         'Gemini_Generated_Image_lno85mlno85mlno8.png')

TEAL   = '#0d7f7a'
NAVY   = '#263238'
P1C    = '#1565c0'
P2C    = '#e65100'
GREEN  = '#2e7d32'
PURPLE = '#6a1b9a'
LGRAY  = '#f5f7f8'
MGRAY  = '#dde3e8'
ORANGE = '#e87722'

A4_W, A4_H = 8.27, 11.69
MX = 0.35
MY = 0.28
CW = A4_W - 2 * MX   # 7.57"


# ── drawing helpers ──────────────────────────────────────────────────────────

def _page():
    fig = plt.figure(figsize=(A4_W, A4_H), facecolor='white', dpi=150)
    ax  = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, A4_W)
    ax.set_ylim(0, A4_H)
    ax.axis('off')
    return fig, ax


def rrect(ax, x, y, w, h, fc, ec='none', lw=1, r=0.05, alpha=1, zo=2):
    r = min(r, w/2, h/2)
    ax.add_patch(patches.FancyBboxPatch(
        (x + r, y + r), max(1e-3, w - 2*r), max(1e-3, h - 2*r),
        boxstyle=f'round,pad={r}', facecolor=fc, edgecolor=ec,
        linewidth=lw, alpha=alpha, zorder=zo, clip_on=False))


def sec_bar(ax, y, title, color=NAVY, h=0.30, fs=8.5):
    """Solid-color section header; returns y just above the bar (including gap)."""
    rrect(ax, MX, y, CW, h, fc=color, zo=3)
    ax.text(MX + 0.14, y + h/2, title, va='center', ha='left',
            fontsize=fs, fontweight='bold', color='white', zorder=4)
    return y + h + 0.13


def bullet_row(ax, x, y, text, fs=8, color=NAVY):
    ax.text(x, y, '•', va='top', ha='left', fontsize=fs + 0.5, color=color)
    ax.text(x + 0.20, y, text, va='top', ha='left', fontsize=fs, color=color)


def num_step(ax, x, y, n, text, color=NAVY, fs=8):
    ax.add_patch(plt.Circle((x + 0.115, y - 0.115), 0.105,
                             facecolor=color, edgecolor='none', zorder=3))
    ax.text(x + 0.115, y - 0.115, str(n), va='center', ha='center',
            fontsize=6.5, fontweight='bold', color='white', zorder=4)
    ax.text(x + 0.28, y, text, va='top', ha='left', fontsize=fs, color=color)


def action_box(ax, y, label, desc, color, h=0.50):
    rrect(ax, MX, y, CW, h, fc=LGRAY, ec=MGRAY, lw=0.5, r=0.06, zo=2)
    rrect(ax, MX, y, 0.90, h, fc=color, r=0.06, zo=3)
    ax.text(MX + 0.45, y + h/2, label, va='center', ha='center',
            fontsize=7.5, fontweight='bold', color='white', zorder=4)
    ax.text(MX + 1.05, y + h/2, desc, va='center', ha='left',
            fontsize=7.5, color=NAVY, zorder=3)


def phase_box(ax, y, title, color, body, h=0.82):
    rrect(ax, MX, y, CW, h, fc=LGRAY, ec=color, lw=0.8, r=0.06, zo=2)
    # colored title strip
    rrect(ax, MX, y + h - 0.28, CW, 0.28, fc=color, r=0.04, zo=3)
    ax.text(MX + 0.18, y + h - 0.14, title, va='center', ha='left',
            fontsize=8, fontweight='bold', color='white', zorder=4)
    ax.text(MX + 0.16, y + h - 0.40, body, va='top', ha='left',
            fontsize=7.5, color=NAVY, zorder=3)


def page_num(ax, n, total=4):
    ax.text(A4_W/2, MY - 0.05, f'{n} / {total}', ha='center', va='center',
            fontsize=7, color='#bbb', zorder=3)


def corner_dec(ax, cx, cy, sx, sy):
    ax.plot([cx, cx + sx*0.45], [cy, cy], color=TEAL, lw=1.4,
            solid_capstyle='round', zorder=3)
    ax.plot([cx, cx], [cy, cy + sy*0.45], color=TEAL, lw=1.4,
            solid_capstyle='round', zorder=3)
    ax.plot(cx + sx*0.45, cy, 'o', color=ORANGE, markersize=3.5, zorder=4)
    ax.plot(cx, cy + sy*0.45, 'o', color=ORANGE, markersize=3.5, zorder=4)


# ── breadboard mini-diagram ──────────────────────────────────────────────────
def draw_mini_board(ax, cx, cy, scale=0.90):
    """Simplified breadboard showing row connections, ravine and rails."""
    rows = 4
    cols_L = ['A', 'B', 'C', 'D', 'E']
    cols_R = ['F', 'G', 'H', 'I', 'J']
    hr = 0.065 * scale           # hole radius
    cs = 0.20 * scale            # column step
    rs = 0.20 * scale            # row step

    rail_x_L = cx - (len(cols_L) + 1.5) * cs
    rail_x_R = cx + (len(cols_R) + 1.5) * cs
    lx = {}
    lx['+L'] = rail_x_L
    lx['-L'] = rail_x_L + cs
    for i, c in enumerate(cols_L):
        lx[c] = cx - (len(cols_L) - i - 0.5) * cs - cs * 0.5
    # ravine gap
    ravine_cx = cx
    for i, c in enumerate(cols_R):
        lx[c] = cx + (i + 0.5) * cs + cs * 0.5
    lx['+R'] = rail_x_R - cs
    lx['-R'] = rail_x_R

    board_x0 = lx['+L'] - cs * 0.6
    board_x1 = lx['-R'] + cs * 0.6
    board_y0 = cy - (rows + 0.3) * rs
    board_y1 = cy + 0.5 * rs
    rrect(ax, board_x0, board_y0, board_x1 - board_x0, board_y1 - board_y0,
          fc='#f0f4f8', ec=NAVY, lw=0.8, r=0.06, zo=5)

    # ravine
    rv_x0 = lx['E'] + cs * 0.38
    rv_x1 = lx['F'] - cs * 0.38
    ax.add_patch(patches.Rectangle((rv_x0, board_y0), rv_x1 - rv_x0, board_y1 - board_y0,
                                   facecolor='#dde3e8', edgecolor='none', zorder=6))
    ax.text((rv_x0 + rv_x1)/2, (board_y0 + board_y1)/2, 'RAV.',
            ha='center', va='center', fontsize=4, color='#90a4ae',
            rotation=90, zorder=7)

    # rail shading
    for rx, c in [(lx['+L'], '#c62828'), (lx['+R'], '#c62828'),
                  (lx['-L'], '#37474f'), (lx['-R'], '#37474f')]:
        ax.add_patch(patches.Rectangle((rx - cs*0.38, board_y0), cs*0.76,
                                       board_y1 - board_y0,
                                       facecolor=c, alpha=0.10, zorder=6))

    # holes
    for row in range(rows):
        ry = cy - row * rs
        for key, fc, ec in (
            [('+L', '#ef9a9a', '#c62828'), ('-L', '#90a4ae', '#37474f')] +
            [(c, '#bdbdbd', '#757575') for c in cols_L + cols_R] +
            [('+R', '#ef9a9a', '#c62828'), ('-R', '#90a4ae', '#37474f')]
        ):
            x = lx[key]
            ax.add_patch(plt.Circle((x, ry), hr, fc=fc, ec=ec, lw=0.5, zorder=8))
            ax.add_patch(plt.Circle((x, ry), hr * 0.38, fc='white', ec='none', zorder=9))

    # row connection brackets (left half)
    for row in range(rows):
        ry = cy - row * rs
        x0 = lx['A'] - hr * 0.8
        x1 = lx['E'] + hr * 0.8
        ax.plot([x0, x1], [ry - hr * 1.8, ry - hr * 1.8],
                color=P1C, lw=0.6, alpha=0.5, zorder=7)

    # col labels
    top_y = cy + 0.22 * scale
    for c in cols_L + cols_R:
        ax.text(lx[c], top_y, c, ha='center', va='center',
                fontsize=4.5, fontweight='bold', color=NAVY, zorder=10)
    for key, sym, c in [('+L', '+', '#c62828'), ('-L', '−', '#37474f'),
                        ('+R', '+', '#c62828'), ('-R', '−', '#37474f')]:
        ax.text(lx[key], top_y, sym, ha='center', va='center',
                fontsize=5.5, fontweight='bold', color=c, zorder=10)

    # example: resistor placed directly between row 1 (rail row) and row 2 —
    # rail connections are automatic, no wire needed
    example_row = 1
    rx_col = lx['A']
    rx_y0 = cy - 2 * rs
    rx_y1 = cy - example_row * rs
    ax.plot([rx_col, rx_col], [rx_y0, rx_y1], color=P2C, lw=1.4,
            linestyle='--', alpha=0.8, zorder=10)
    ax.text(rx_col + hr * 2.5, (rx_y0 + rx_y1)/2, '100Ω', ha='left', va='center',
            fontsize=4.5, color=P2C, zorder=11)

    # labels
    ax.text(lx['+L'], board_y0 - 0.08, '+rail', ha='center', va='top',
            fontsize=4, color='#c62828', zorder=10)
    ax.text(lx['-L'], board_y0 - 0.08, '−rail', ha='center', va='top',
            fontsize=4, color='#37474f', zorder=10)


# ════════════════════════════════════════════════════════════════════════════
# TEXT CONTENT
# ════════════════════════════════════════════════════════════════════════════
LANGS = {
    'en': dict(
        # Cover
        subtitle='An Educational Electronics Game',
        instructions_title='GAME INSTRUCTIONS',
        pills=['2 Players', 'Ages 14+', '30–45 min'],

        # Page 2
        p2_header='OVERVIEW & SETUP',
        obj_header='OBJECTIVE',
        obj_text='Build circuits on the shared breadboard to match Objective Cards and score the most points.',
        comp_header='COMPONENTS',
        comp_list=[
            '1 × A4 Game Board',
            '40 × 100 Ω Resistor cards',
            '20 × 200 Ω Resistor cards',
            '20 × 300 Ω Resistor cards',
            '40 × 10 µF Capacitor cards',
            '20 × 20 µF Capacitor cards',
            '20 × 30 µF Capacitor cards',
            '32 × Objective cards',
        ],
        setup_header='SETUP',
        setup_steps=[
            'Place the board between both players.',
            'Shuffle Component cards; deal each player 15 cards as their starting hand.',
            'Shuffle Objective cards. Each player draws 3 Objective cards face-up.',
            'Decide who goes first — Player 1 begins.',
        ],

        # Page 3
        p3_header='HOW TO PLAY',
        turn_header='YOUR TURN',
        turn_intro='On your turn, perform up to 3 Actions:',
        actions=[
            ('PLACE',  P2C,  'Play a card from your hand and place the component on a valid hole on the board.'),
            ('DRAW',   P1C,  'Take 1 card from the shared Component deck.'),
            ('COMPLETE', NAVY, 'Finalize your circuit: the board is checked against your Objective Cards and you score any that match.'),
        ],
        phases_header='OBJECTIVE TIERS',
        phases=[
            ('SETUP  —  2 components', P1C,
             'Simple series or parallel objectives. Rail connections are automatic — no\n'
             'wiring needed, just place Resistors/Capacitors directly to build a circuit.'),
            ('BUILD  —  3 components, EXPERT  —  4 components', P2C,
             'Place more Resistors and Capacitors to hit higher-tier Objective Card values\n'
             'for more points. All tiers are available from the start.'),
        ],
        board_header='THE BREADBOARD',
        board_rules=[
            'Holes A–E in the same row are internally connected (left half).',
            'Holes F–J in the same row are internally connected (right half).',
            'The Ravine divides the board into two independent halves.',
            'Each half has its own + rail and − rail — you can work on either side.',
            'A valid circuit must connect a + rail to a − rail through your components.',
        ],

        # Page 4
        p4_header='CIRCUITS & SCORING',
        phys_header='CIRCUIT PHYSICS',
        col_series='Series',
        col_parallel='Parallel',
        row_R='RESISTANCE',
        row_C='CAPACITANCE',
        formula_sR='R = R₁ + R₂',
        formula_pR='R = R₁ × R₂ / (R₁ + R₂)',
        formula_sC='1/C = 1/C₁ + 1/C₂',
        formula_pC='C = C₁ + C₂',
        note_R='Resistors in parallel → lower resistance.',
        note_C='Capacitors in series → lower capacitance.',
        examples_header='EXAMPLES',
        examples=[
            '100 Ω + 200 Ω  in series     →  300 Ω',
            '100 Ω || 100 Ω  in parallel   →   50 Ω',
            '10 µF + 10 µF  in series     →    5 µF',
            '10 µF || 20 µF  in parallel   →  30 µF',
        ],
        scoring_header='SCORING',
        scoring_rules=[
            'At the end of each of your turns, check your Objective Cards.',
            'If your components on the board match an Objective target → score its points.',
            'Discard the completed Objective and draw a new one from the deck.',
            'Only your own components count toward your objectives.',
        ],
        tiers_header='OBJECTIVE TIERS',
        tiers=[
            ('SETUP',        GREEN,  '30–40 pts', '2 components'),
            ('BUILD',        P2C,    '40–45 pts', '3 components'),
            ('EXPERT',       PURPLE, '65 pts',    '4 components'),
        ],
        winning_header='WINNING',
        winning_text=(
            'After 6 turns each, the player with the most total points wins!\n'
            'Tie-break: the player who completed more Objective Cards wins.'
        ),
    ),

    'es': dict(
        # Cover
        subtitle='Un Juego Educativo de Electrónica',
        instructions_title='INSTRUCCIONES DEL JUEGO',
        pills=['2 Equipos', '14+ años', '30–45 min'],

        # Page 2
        p2_header='DESCRIPCIÓN Y PREPARACIÓN',
        obj_header='OBJETIVO',
        obj_text='Construye circuitos en la protoboard compartida para cumplir Cartas Objetivo y acumular la mayor cantidad de puntos.',
        comp_header='COMPONENTES',
        comp_list=[
            '1 × Tablero A4 de juego',
            '40 × Cartas Resistor 100 Ω',
            '20 × Cartas Resistor 200 Ω',
            '20 × Cartas Resistor 300 Ω',
            '40 × Cartas Capacitor 10 µF',
            '20 × Cartas Capacitor 20 µF',
            '20 × Cartas Capacitor 30 µF',
            '32 × Cartas Objetivo',
        ],
        setup_header='PREPARACIÓN',
        setup_steps=[
            'Coloca el tablero entre los dos equipos.',
            'Baraja las Cartas de Componentes; reparte 15 cartas a cada equipo.',
            'Baraja las Cartas Objetivo. Cada equipo roba 3 Cartas Objetivo boca arriba.',
            'Decide quién comienza — el Equipo 1 juega primero.',
        ],

        # Page 3
        p3_header='CÓMO JUGAR',
        turn_header='TU TURNO',
        turn_intro='En tu turno, realiza hasta 3 Acciones:',
        actions=[
            ('COLOCAR', P2C,  'Juega una carta de tu mano y coloca el componente en un agujero válido del tablero.'),
            ('ROBAR',   P1C,  'Toma 1 carta del mazo compartido de Componentes.'),
            ('COMPLETAR', NAVY, 'Finaliza tu circuito: se revisa contra tus Cartas Objetivo y anotas los puntos de las que coincidan.'),
        ],
        phases_header='NIVELES DE OBJETIVO',
        phases=[
            ('PREPARACIÓN  —  2 componentes', P1C,
             'Objetivos simples en serie o paralelo. Las conexiones a los rieles son\n'
             'automáticas — no se necesitan cables, solo coloca Resistores/Capacitores.'),
            ('CONSTRUCCIÓN  —  3 componentes, EXPERTO  —  4 componentes', P2C,
             'Coloca más Resistores y Capacitores para alcanzar valores de mayor nivel\n'
             'en tus Cartas Objetivo y ganar más puntos. Todos los niveles están disponibles desde el inicio.'),
        ],
        board_header='LA PROTOBOARD',
        board_rules=[
            'Los agujeros A–E en la misma fila están conectados internamente (mitad izquierda).',
            'Los agujeros F–J en la misma fila están conectados internamente (mitad derecha).',
            'La Ranura divide el tablero en dos mitades independientes.',
            'Cada mitad tiene su propio riel + y riel − — puedes trabajar en cualquier lado.',
            'Un circuito válido debe conectar un riel + con un riel − a través de los componentes.',
        ],

        # Page 4
        p4_header='CIRCUITOS Y PUNTUACIÓN',
        phys_header='FÍSICA DE CIRCUITOS',
        col_series='Serie',
        col_parallel='Paralelo',
        row_R='RESISTENCIA',
        row_C='CAPACITANCIA',
        formula_sR='R = R₁ + R₂',
        formula_pR='R = R₁ × R₂ / (R₁ + R₂)',
        formula_sC='1/C = 1/C₁ + 1/C₂',
        formula_pC='C = C₁ + C₂',
        note_R='Resistores en paralelo → resistencia menor.',
        note_C='Capacitores en serie → capacitancia menor.',
        examples_header='EJEMPLOS',
        examples=[
            '100 Ω + 200 Ω  en serie      →  300 Ω',
            '100 Ω || 100 Ω  en paralelo   →   50 Ω',
            '10 µF + 10 µF  en serie      →    5 µF',
            '10 µF || 20 µF  en paralelo   →  30 µF',
        ],
        scoring_header='PUNTUACIÓN',
        scoring_rules=[
            'Al final de cada uno de tus turnos, revisa tus Cartas Objetivo.',
            'Si tus componentes en el tablero cumplen un Objetivo → anota sus puntos.',
            'Descarta el Objetivo completado y roba una nueva Carta Objetivo.',
            'Solo tus propios componentes cuentan para tus objetivos.',
        ],
        tiers_header='NIVELES DE OBJETIVOS',
        tiers=[
            ('PREPARACIÓN', GREEN,  '30–40 pts', '2 componentes'),
            ('CONSTRUCCIÓN', P2C,   '40–45 pts', '3 componentes'),
            ('EXPERTO',     PURPLE, '65 pts',    '4 componentes'),
        ],
        winning_header='GANADOR',
        winning_text=(
            '¡Después de 6 turnos cada uno, el equipo con más puntos gana!\n'
            'Empate: gana quien haya completado más Cartas Objetivo.'
        ),
    ),
}


# ════════════════════════════════════════════════════════════════════════════
# PAGE DRAWING FUNCTIONS
# ════════════════════════════════════════════════════════════════════════════

def draw_cover(ax, T):
    # Teal top band
    band_y = 7.50
    ax.add_patch(patches.Rectangle((0, band_y), A4_W, A4_H - band_y,
                                   facecolor=TEAL, edgecolor='none', zorder=1))

    # Logo centred in band
    if os.path.exists(LOGO_PATH):
        logo = mpimg.imread(LOGO_PATH)
        h_px, w_px = logo.shape[:2]
        lw = 4.0
        lh = lw * h_px / w_px
        lx = (A4_W - lw) / 2
        ly = band_y + (A4_H - band_y - lh) / 2 + 0.05
        ax.add_patch(patches.Rectangle((lx, ly), lw, lh,
                                       facecolor='white', edgecolor='none', zorder=2))
        ax.imshow(logo, extent=[lx, lx+lw, ly, ly+lh], aspect='auto', zorder=3)

    ax.plot([0, A4_W], [band_y, band_y], color='white', lw=1.2, zorder=3)

    # Title block
    ax.text(A4_W/2, 7.05, 'CIRCUIT MASTER',
            ha='center', va='center', fontsize=26, fontweight='bold', color=TEAL)
    ax.text(A4_W/2, 6.58, T['subtitle'],
            ha='center', va='center', fontsize=9, color=NAVY, alpha=0.70)
    ax.plot([MX + 1.0, A4_W - MX - 1.0], [6.27, 6.27],
            color=TEAL, lw=1.0, alpha=0.40)
    ax.text(A4_W/2, 5.80, T['instructions_title'],
            ha='center', va='center', fontsize=15, fontweight='bold', color=NAVY)

    # Info pills
    pills  = T['pills']
    pill_w = 1.70
    pill_h = 0.36
    gap    = 0.22
    total  = len(pills) * pill_w + (len(pills) - 1) * gap
    px0    = (A4_W - total) / 2
    pill_colors = [TEAL, P1C, P2C]
    for i, (pill, pc) in enumerate(zip(pills, pill_colors)):
        px = px0 + i * (pill_w + gap)
        rrect(ax, px, 5.18, pill_w, pill_h, fc=pc, r=0.10, zo=3)
        ax.text(px + pill_w/2, 5.18 + pill_h/2, pill,
                ha='center', va='center', fontsize=8, fontweight='bold',
                color='white', zorder=4)

    # Decorative box in lower half
    rrect(ax, MX + 0.10, 1.60, CW - 0.20, 3.10,
          fc=LGRAY, ec=MGRAY, lw=0.7, r=0.10, zo=2)

    # Quick-reference icons inside box
    icons = [
        (MX + 0.60, 3.50, '🔌', TEAL,  'Wires first'),
        (MX + 0.60, 2.95, '⚡', P2C,   'Then resistors & capacitors'),
        (MX + 0.60, 2.40, '🏆', GREEN, 'Most points wins'),
    ] if False else []   # skip emoji path — use text labels instead

    # Simple numbered quick-tips
    tips_en = [
        ('1', 'No wiring needed — rail connections are automatic on both sides of the board.'),
        ('2', 'Place Resistors/Capacitors directly to build series or parallel circuits.'),
        ('3', 'Match the Objective Card value to score points on your turn.'),
        ('4', 'Higher-tier objectives (more components) are worth more points.'),
    ]
    tips_es = [
        ('1', 'No se necesitan cables — las conexiones a los rieles son automáticas en ambos lados.'),
        ('2', 'Coloca Resistores/Capacitores directamente para armar circuitos en serie o paralelo.'),
        ('3', 'Haz coincidir el valor de la Carta Objetivo para anotar puntos.'),
        ('4', 'Los objetivos de mayor nivel (más componentes) valen más puntos.'),
    ]
    tips = tips_es if T.get('pills', [''])[0].startswith('2 E') else tips_en
    quick_label = 'QUICK TIPS' if tips is tips_en else 'CONSEJOS RÁPIDOS'
    ax.text(A4_W/2, 4.52, quick_label,
            ha='center', va='center', fontsize=8, fontweight='bold', color=NAVY)
    ax.plot([MX + 0.50, A4_W - MX - 0.50], [4.35, 4.35],
            color=MGRAY, lw=0.8)
    for i, (n, tip) in enumerate(tips):
        ty = 4.15 - i * 0.50
        ax.add_patch(plt.Circle((MX + 0.40, ty - 0.10), 0.10,
                                facecolor=TEAL, edgecolor='none', zorder=3))
        ax.text(MX + 0.40, ty - 0.10, n, ha='center', va='center',
                fontsize=6, fontweight='bold', color='white', zorder=4)
        ax.text(MX + 0.60, ty, tip, va='top', ha='left', fontsize=7.5, color=NAVY)

    # Corner decorations
    corner_dec(ax, MX, MY, 1, 1)
    corner_dec(ax, A4_W - MX, MY, -1, 1)
    page_num(ax, 1)


def draw_p2(ax, T):
    # Top strip
    ax.add_patch(patches.Rectangle((0, A4_H - 0.46), A4_W, 0.46,
                                   facecolor=TEAL, edgecolor='none', zorder=2))
    ax.text(A4_W/2, A4_H - 0.23, T['p2_header'],
            ha='center', va='center', fontsize=10, fontweight='bold', color='white', zorder=3)

    y = A4_H - 0.60

    # OBJECTIVE
    sec_bar(ax, y, T['obj_header'], color=TEAL)
    y -= 0.32 + 0.06
    ax.text(MX + 0.12, y, T['obj_text'], va='top', ha='left', fontsize=8, color=NAVY)
    y -= 0.34

    # COMPONENTS — two columns
    y -= 0.08
    sec_bar(ax, y, T['comp_header'], color=NAVY)
    y -= 0.32 + 0.08
    items = T['comp_list']
    half  = (len(items) + 1) // 2
    col1, col2 = items[:half], items[half:]
    y_comp = y
    for ci, col in enumerate([col1, col2]):
        cx = MX + 0.12 if ci == 0 else MX + CW / 2 + 0.08
        yy = y_comp
        for item in col:
            bullet_row(ax, cx, yy, item, fs=7.8)
            yy -= 0.285
    y = y_comp - half * 0.285 - 0.10

    # SETUP
    y -= 0.06
    sec_bar(ax, y, T['setup_header'], color=GREEN)
    y -= 0.32 + 0.10
    for i, step in enumerate(T['setup_steps'], 1):
        num_step(ax, MX + 0.12, y, i, step, fs=8)
        y -= 0.385

    page_num(ax, 2)


def draw_p3(ax, T):
    # Top strip
    ax.add_patch(patches.Rectangle((0, A4_H - 0.46), A4_W, 0.46,
                                   facecolor=TEAL, edgecolor='none', zorder=2))
    ax.text(A4_W/2, A4_H - 0.23, T['p3_header'],
            ha='center', va='center', fontsize=10, fontweight='bold', color='white', zorder=3)

    y = A4_H - 0.60

    # YOUR TURN + ACTIONS
    sec_bar(ax, y, T['turn_header'], color=P2C)
    y -= 0.32 + 0.08
    ax.text(MX + 0.12, y, T['turn_intro'], va='top', ha='left', fontsize=8, color=NAVY)
    y -= 0.32

    for (label, color, desc) in T['actions']:
        action_box(ax, y - 0.50, label, desc, color, h=0.50)
        y -= 0.64

    # GAME PHASES
    y -= 0.05
    sec_bar(ax, y, T['phases_header'], color=P1C)
    y -= 0.32 + 0.08
    for (title, color, body) in T['phases']:
        phase_box(ax, y - 0.82, title, color, body, h=0.82)
        y -= 0.96

    # THE BREADBOARD
    y -= 0.04
    sec_bar(ax, y, T['board_header'], color=NAVY)
    y -= 0.32 + 0.08

    # Left: rules; Right: mini diagram
    rules_w = CW * 0.57
    diag_x  = MX + rules_w + 0.15

    for rule in T['board_rules']:
        bullet_row(ax, MX + 0.12, y, rule, fs=7.5, color=NAVY)
        y -= 0.285

    # Mini breadboard diagram
    draw_mini_board(ax, cx=diag_x + 1.45, cy=y + 0.285 * 3.0, scale=0.85)

    page_num(ax, 3)


def draw_p4(ax, T):
    # Top strip
    ax.add_patch(patches.Rectangle((0, A4_H - 0.46), A4_W, 0.46,
                                   facecolor=TEAL, edgecolor='none', zorder=2))
    ax.text(A4_W/2, A4_H - 0.23, T['p4_header'],
            ha='center', va='center', fontsize=10, fontweight='bold', color='white', zorder=3)

    y = A4_H - 0.60

    # CIRCUIT PHYSICS — formula grid
    sec_bar(ax, y, T['phys_header'], color=TEAL)
    y -= 0.32 + 0.08

    # Grid layout
    col_w   = CW / 2 - 0.05
    row_h   = 0.66
    grid_x0 = MX
    grid_x1 = MX + col_w + 0.10

    # Header row
    hh = 0.26
    rrect(ax, grid_x0, y - hh, col_w, hh, fc=MGRAY, r=0.04, zo=3)
    rrect(ax, grid_x1, y - hh, col_w, hh, fc=MGRAY, r=0.04, zo=3)
    ax.text(grid_x0 + col_w/2, y - hh/2, T['col_series'],
            ha='center', va='center', fontsize=8, fontweight='bold', color=NAVY, zorder=4)
    ax.text(grid_x1 + col_w/2, y - hh/2, T['col_parallel'],
            ha='center', va='center', fontsize=8, fontweight='bold', color=NAVY, zorder=4)
    y -= hh + 0.05

    for (row_label, color, fs_R, fs_P) in [
        (T['row_R'], P2C,    T['formula_sR'], T['formula_pR']),
        (T['row_C'], P1C, T['formula_sC'], T['formula_pC']),
    ]:
        for xi, (formula, note_key) in enumerate([
            (fs_R, 'note_R'),
            (fs_P, 'note_C'),
        ]):
            gx = grid_x0 if xi == 0 else grid_x1
            rrect(ax, gx, y - row_h, col_w, row_h, fc=LGRAY, ec=MGRAY, lw=0.5, r=0.05, zo=2)
            ax.text(gx + 0.12, y - 0.12, row_label, va='top', ha='left',
                    fontsize=6.5, fontweight='bold', color=color, zorder=3)
            ax.text(gx + col_w/2, y - row_h/2 - 0.04, formula,
                    ha='center', va='center', fontsize=9.5, fontweight='bold',
                    color=NAVY, zorder=3, family='monospace')
        y -= row_h + 0.07

    # Key notes
    ax.text(MX + 0.10, y, '▸ ' + T['note_R'], va='top', ha='left', fontsize=7.5, color=P2C)
    y -= 0.26
    ax.text(MX + 0.10, y, '▸ ' + T['note_C'], va='top', ha='left', fontsize=7.5, color=P1C)
    y -= 0.30

    # EXAMPLES box
    y -= 0.06
    rrect(ax, MX, y - len(T['examples'])*0.25 - 0.18, CW,
          len(T['examples'])*0.25 + 0.30, fc='#fff8f0', ec='#ffe0b2', lw=0.6, r=0.06, zo=2)
    ax.text(MX + CW/2, y - 0.02, T['examples_header'],
            ha='center', va='top', fontsize=7.5, fontweight='bold', color=P2C)
    y -= 0.24
    for ex in T['examples']:
        ax.text(MX + CW/2, y, ex, ha='center', va='top',
                fontsize=8, color=NAVY, family='monospace')
        y -= 0.25
    y -= 0.05

    # SCORING
    y -= 0.06
    sec_bar(ax, y, T['scoring_header'], color=GREEN)
    y -= 0.32 + 0.08
    for rule in T['scoring_rules']:
        bullet_row(ax, MX + 0.12, y, rule, fs=7.8)
        y -= 0.285

    # OBJECTIVE TIERS
    y -= 0.06
    sec_bar(ax, y, T['tiers_header'], color=PURPLE)
    y -= 0.32 + 0.08
    tier_w = CW / len(T['tiers']) - 0.08
    for i, (label, color, pts, comps) in enumerate(T['tiers']):
        tx = MX + i * (tier_w + 0.08)
        rrect(ax, tx, y - 0.58, tier_w, 0.58, fc=color, r=0.06, alpha=0.92, zo=3)
        ax.text(tx + tier_w/2, y - 0.15, label, ha='center', va='center',
                fontsize=7, fontweight='bold', color='white', zorder=4)
        ax.text(tx + tier_w/2, y - 0.33, pts, ha='center', va='center',
                fontsize=8.5, fontweight='bold', color='white', zorder=4)
        ax.text(tx + tier_w/2, y - 0.50, comps, ha='center', va='center',
                fontsize=6.5, color='white', alpha=0.88, zorder=4)
    y -= 0.68

    # WINNING
    y -= 0.08
    rrect(ax, MX, y - 0.56, CW, 0.62, fc='#e8f5e9', ec=GREEN, lw=0.7, r=0.07, zo=2)
    ax.text(MX + 0.16, y - 0.06, '🏆 ' + T['winning_header'] if False else T['winning_header'],
            va='top', ha='left', fontsize=9, fontweight='bold', color=GREEN, zorder=3)
    ax.text(MX + 0.14, y - 0.27, T['winning_text'], va='top', ha='left',
            fontsize=8, color=NAVY, zorder=3)

    page_num(ax, 4)


# ════════════════════════════════════════════════════════════════════════════
# GENERATE PDFs
# ════════════════════════════════════════════════════════════════════════════
for lang_code, T in LANGS.items():
    fname = f'instructions_{lang_code}.pdf'
    with PdfPages(fname) as pdf:
        for draw_fn in [draw_cover, draw_p2, draw_p3, draw_p4]:
            fig, ax = _page()
            draw_fn(ax, T)
            pdf.savefig(fig, dpi=150)
            plt.close(fig)
    print(f'Guardado / Saved: {fname}')
