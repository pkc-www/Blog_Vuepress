"""Circuit topology diagrams for the 电力电子进阶 blog series (drawn with schemdraw).

Usage: python3 topologies.py <output-dir>
All circuits are redrawn from the standard textbook topologies (Erickson & Maksimović,
王兆安《电力电子技术》, De Doncker 1991 for DAB), so there is no third-party image copyright.
"""
import sys
import schemdraw
import schemdraw.elements as elm
from matplotlib import font_manager

font_manager.fontManager.addfont("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc")
schemdraw.use("matplotlib")
schemdraw.config(font="WenQuanYi Zen Hei", fontsize=13, lw=1.6)
OUT = sys.argv[1]
DPI = 160


def wire(d, *pts):
    for a, b in zip(pts, pts[1:]):
        d += elm.Line().endpoints(a, b)


def hop_v(d, x, y, y_from, y_to):
    """Vertical wire from y_from to y_to at x, hopping over a horizontal wire at height y."""
    s = 1 if y_to > y_from else -1
    wire(d, (x, y_from), (x, y - 0.22 * s))
    d += elm.Arc2(k=0.9).at((x, y - 0.22 * s)).to((x, y + 0.22 * s))
    wire(d, (x, y + 0.22 * s), (x, y_to))


def dot(d, p, opn=False):
    d += elm.Dot(open=opn, radius=0.08).at(p)


def label(d, p, text, size=12, **kw):
    d += elm.Label().at(p).label(text, fontsize=size, **kw)


def output_stage(d, x0, ytop, ybot, cname="C", rname="R", vpol=("+", "$-$")):
    d += elm.Capacitor().endpoints((x0, ytop), (x0, ybot)).label(cname, loc="bottom")
    dot(d, (x0, ytop)); dot(d, (x0, ybot))
    d += elm.Resistor().endpoints((x0 + 2, ytop), (x0 + 2, ybot)).label(rname, loc="bottom")
    wire(d, (x0, ytop), (x0 + 2, ytop)); wire(d, (x0, ybot), (x0 + 2, ybot))
    wire(d, (x0 + 2, ytop), (x0 + 3, ytop)); wire(d, (x0 + 2, ybot), (x0 + 3, ybot))
    d += elm.Gap().endpoints((x0 + 3, ytop), (x0 + 3, ybot)).label([vpol[0], "$V_o$", vpol[1]])


def mosfet(d, x, ytop, name):
    """Vertical N-MOSFET drawn from primitives, with antiparallel body diode on the right.
    Drain (x, ytop), source (x, ytop-1.5), gate lead to the left."""
    y = ytop
    wire(d, (x, y), (x, y - 0.45), (x - 0.35, y - 0.45))            # drain lead
    wire(d, (x, y - 1.5), (x, y - 1.05), (x - 0.35, y - 1.05))      # source lead
    wire(d, (x - 0.35, y - 0.3), (x - 0.35, y - 1.2))               # channel
    wire(d, (x - 0.5, y - 0.45), (x - 0.5, y - 1.05))               # gate plate
    wire(d, (x - 0.5, y - 0.75), (x - 0.95, y - 0.75))              # gate lead
    d += elm.Line(arrow="->", arrowwidth=0.16, arrowlength=0.18).endpoints((x, y - 0.75), (x - 0.35, y - 0.75))  # NMOS body arrow
    wire(d, (x, y - 0.75), (x, y - 1.05))
    bx = x + 0.6
    wire(d, (x, y - 0.25), (bx, y - 0.25))
    wire(d, (x, y - 1.25), (bx, y - 1.25))
    d += elm.Diode(scale=0.55).endpoints((bx, y - 1.25), (bx, y - 0.25))
    label(d, (x + 1.25, y - 0.75), name)
    return (x, y), (x, y - 1.5)


def full_bridge(d, x1, x2, ytop, ybot, names):
    """Two-leg MOSFET bridge between rails; returns leg midpoints."""
    ymid = (ytop + ybot) / 2
    mids = []
    for x, (nu, nl) in zip((x1, x2), names):
        dt, st = mosfet(d, x, ymid + 1.75, nu)
        db, sb = mosfet(d, x, ymid - 0.25, nl)
        wire(d, (x, ytop), dt); wire(d, st, db); wire(d, sb, (x, ybot))
        dot(d, (x, ymid))
        mids.append((x, ymid))
    wire(d, (x1, ytop), (x2, ytop)); wire(d, (x1, ybot), (x2, ybot))
    return mids


def xfmr(d, p1, ratio):
    t = elm.Transformer(t1=4, t2=4, core=True).right().anchor("p1").at(p1)
    d += t
    label(d, ((t.p1[0] + t.s1[0]) / 2, t.p1[1] + 0.6), ratio)
    return t


def pol_dot(d, t, prim_top=True, sec_top=True):
    """Dot-convention markers next to the windings."""
    py = t.p1[1] - 0.2 if prim_top else t.p2[1] + 0.2
    sy = t.s1[1] - 0.2 if sec_top else t.s2[1] + 0.2
    d += elm.Dot(radius=0.09).at((t.p1[0] - 0.3, py))
    d += elm.Dot(radius=0.09).at((t.s1[0] + 0.3, sy))


def save(d, name):
    d.save(f"{OUT}/{name}", dpi=DPI)


# ------------------------------------------------------------------ Buck
with schemdraw.Drawing(show=False) as d:
    d += elm.SourceV().endpoints((0, 0), (0, 3)).label("$V_{in}$", loc="bottom", ofst=0.3)
    d += elm.Switch(action="close").endpoints((0, 3), (3, 3)).label("S", loc="top")
    d += elm.Diode().endpoints((3, 0), (3, 3)).label("D", loc="bottom")
    dot(d, (3, 3)); dot(d, (3, 0))
    d += elm.Inductor2(loops=3).endpoints((3, 3), (6, 3)).label("L", loc="top").label("$i_L$ →", loc="bottom", fontsize=11)
    wire(d, (0, 0), (6, 0))
    output_stage(d, 6, 3, 0)
    save(d, "topo-buck.png")

# ------------------------------------------------------------------ Boost
with schemdraw.Drawing(show=False) as d:
    d += elm.SourceV().endpoints((0, 0), (0, 3)).label("$V_{in}$", loc="bottom", ofst=0.3)
    d += elm.Inductor2(loops=3).endpoints((0, 3), (3, 3)).label("L", loc="top").label("$i_L$ →", loc="bottom", fontsize=11)
    d += elm.Switch(action="close").endpoints((3, 3), (3, 0)).label("S", loc="bottom")
    dot(d, (3, 3)); dot(d, (3, 0))
    d += elm.Diode().endpoints((3, 3), (6, 3)).label("D", loc="top")
    wire(d, (0, 0), (6, 0))
    output_stage(d, 6, 3, 0)
    save(d, "topo-boost.png")

# ------------------------------------------------------------------ Buck-Boost (inverting)
with schemdraw.Drawing(show=False) as d:
    d += elm.SourceV().endpoints((0, 0), (0, 3)).label("$V_{in}$", loc="bottom", ofst=0.3)
    d += elm.Switch(action="close").endpoints((0, 3), (3, 3)).label("S", loc="top")
    d += elm.Inductor2(loops=3).endpoints((3, 3), (3, 0)).label("L", loc="bottom").label("$i_L$ ↓", loc="top", fontsize=11)
    dot(d, (3, 3)); dot(d, (3, 0))
    d += elm.Diode().endpoints((6, 3), (3, 3)).label("D", loc="top")
    wire(d, (0, 0), (6, 0))
    output_stage(d, 6, 3, 0, vpol=("$-$", "+"))
    save(d, "topo-buck-boost.png")

# ------------------------------------------------------------------ Flyback
with schemdraw.Drawing(show=False) as d:
    d += elm.SourceV().endpoints((0, 0), (0, 4)).label("$V_{in}$", loc="bottom", ofst=0.3)
    t = xfmr(d, (2.5, 4), "$N_p : N_s$")
    pol_dot(d, t, prim_top=True, sec_top=False)          # opposite polarity
    wire(d, (0, 4), t.p1)
    d += elm.Switch(action="close").endpoints(t.p2, (t.p2[0], 0)).label("S", loc="bottom")
    wire(d, (0, 0), (t.p2[0], 0))
    d += elm.Diode().endpoints(t.s1, (6, t.s1[1])).label("D", loc="top")
    wire(d, t.s2, (t.s2[0], 0), (6, 0))
    output_stage(d, 6, 4, 0)
    save(d, "topo-flyback.png")


# ------------------------------------------------------------------ Forward (with reset winding)
with schemdraw.Drawing(show=False) as d:
    top, bot = 5, 0
    d += elm.SourceV().endpoints((0, bot), (0, top)).label("$V_{in}$", loc="bottom", ofst=0.3)
    wire(d, (0, top), (4.5, top))
    # reset winding N_r with D3 back to the input rail (drawn as a separate inductor coupled to the core)
    d += elm.Inductor2(loops=3).endpoints((2, bot), (2, 2.6)).label("$N_r$", loc="bottom")
    d += elm.Diode().endpoints((2, 2.6), (2, top)).label("$D_3$", loc="bottom")
    dot(d, (2, top)); dot(d, (2, bot))
    label(d, (2.35, 0.5), "●", size=10)
    t = xfmr(d, (4.5, top), "$N_p : N_s$")
    pol_dot(d, t, prim_top=True, sec_top=True)          # same polarity
    d += elm.Switch(action="close").endpoints(t.p2, (t.p2[0], bot)).label("S", loc="bottom")
    wire(d, (0, bot), (t.p2[0], bot))
    d += elm.Diode().endpoints(t.s1, (7.5, t.s1[1])).label("$D_1$", loc="top")
    d += elm.Diode().endpoints((7.5, bot), (7.5, t.s1[1])).label("$D_2$", loc="bottom")
    dot(d, (7.5, t.s1[1])); dot(d, (7.5, bot))
    wire(d, t.s2, (t.s2[0], bot), (7.5, bot))
    d += elm.Inductor2(loops=3).endpoints((7.5, t.s1[1]), (10, t.s1[1])).label("L", loc="top")
    wire(d, (7.5, bot), (10, bot))
    output_stage(d, 10, t.s1[1], bot)
    save(d, "topo-forward.png")


# ------------------------------------------------------------------ full-bridge isolated / PSFB
def primary_bridge(d, vname="$V_{in}$", with_cap=False):
    top, bot = 5.0, 0.0
    x0 = -1.6 if with_cap else -0.8
    d += elm.SourceV().endpoints((x0, bot), (x0, top)).label(vname, loc="bottom", ofst=0.3)
    if with_cap:
        d += elm.Capacitor().endpoints((0, top), (0, bot)).label("$C_1$", loc="bottom")
        dot(d, (0, top)); dot(d, (0, bot))
    wire(d, (x0, top), (1.5, top)); wire(d, (x0, bot), (1.5, bot))
    dot(d, (1.5, top)); dot(d, (1.5, bot))
    A, B = full_bridge(d, 1.5, 5.5, top, bot, [("S1", "S2"), ("S3", "S4")])
    label(d, (A[0] - 0.3, A[1] + 0.3), "A", size=11)
    label(d, (B[0] - 0.3, B[1] + 0.3), "B", size=11)
    return A, B, top, bot


def route_primary(d, A, B, t, top, series=None):
    """A -> (series inductor) -> p1 over the top rail; B -> p2 directly."""
    wire(d, A, (3.6, A[1]))
    hop_v(d, 3.6, top, A[1], 5.9)
    if series:
        wire(d, (3.6, 5.9), (7.4, 5.9))
        d += elm.Inductor2(loops=2).endpoints((7.4, 5.9), (9.4, 5.9)).label(series, loc="top")
        wire(d, (9.4, 5.9), (t.p1[0], 5.9), t.p1)
    else:
        wire(d, (3.6, 5.9), (t.p1[0], 5.9), t.p1)
    wire(d, B, (7.4, B[1]), (7.4, t.p2[1]), t.p2)


def fb_isolated(name, series):
    with schemdraw.Drawing(show=False) as d:
        A, B, top, bot = primary_bridge(d)
        t = xfmr(d, (10.0, 3.3), "$n:1$")
        pol_dot(d, t)
        route_primary(d, A, B, t, top, series)
        label(d, (8.6, 2.6), "$v_{AB}$", size=12)
        # secondary diode bridge
        xs1, xs2, ytop, ybot, ym = 13.0, 15.0, 5.0, 0.0, 2.5
        for x, (nu, nl) in zip((xs1, xs2), (("$D_1$", "$D_2$"), ("$D_3$", "$D_4$"))):
            d += elm.Diode().endpoints((x, ym), (x, ytop)).label(nu, loc="bottom" if x == xs1 else "top", fontsize=11)
            d += elm.Diode().endpoints((x, ybot), (x, ym)).label(nl, loc="bottom" if x == xs1 else "top", fontsize=11)
            dot(d, (x, ym))
        wire(d, (xs1, ytop), (xs2, ytop)); wire(d, (xs1, ybot), (xs2, ybot))
        wire(d, t.s1, (12.0, t.s1[1]), (12.0, ym), (xs1, ym))
        wire(d, t.s2, (t.s2[0], -0.9), (14.0, -0.9))
        hop_v(d, 14.0, ybot, -0.9, ym)
        wire(d, (14.0, ym), (xs2, ym))
        dot(d, (xs2, ytop)); dot(d, (xs2, ybot))
        d += elm.Inductor2(loops=3).endpoints((xs2, ytop), (18, ytop)).label("$L_o$", loc="top")
        wire(d, (xs2, ybot), (18, ybot))
        output_stage(d, 18, ytop, ybot, cname="$C_o$")
        save(d, name)


fb_isolated("topo-full-bridge-isolated.png", series=None)
fb_isolated("topo-psfb.png", series="$L_r$")

# ------------------------------------------------------------------ DAB
with schemdraw.Drawing(show=False) as d:
    A, B, top, bot = primary_bridge(d, vname="$V_1$", with_cap=True)
    t = xfmr(d, (10.0, 3.3), "$n:1$")
    pol_dot(d, t)
    route_primary(d, A, B, t, top, series="$L$")
    label(d, (5.6, 6.3), "$i_L$ →", size=12)
    label(d, (8.6, 2.6), "$v_p$", size=13)
    # secondary active bridge
    xs1, xs2 = 13.5, 17.5
    C, D = full_bridge(d, xs1, xs2, top, bot, [("Q1", "Q2"), ("Q3", "Q4")])
    label(d, (C[0] - 0.3, C[1] + 0.3), "C", size=11)
    label(d, (D[0] - 0.3, D[1] + 0.3), "D", size=11)
    wire(d, t.s1, (12.0, t.s1[1]), (12.0, C[1]), C)
    wire(d, t.s2, (t.s2[0], -0.9), (16.0, -0.9))
    hop_v(d, 16.0, bot, -0.9, D[1])
    wire(d, (16.0, D[1]), D)
    label(d, (11.75, 2.45), "$v_s$", size=13)
    dot(d, (xs2, top)); dot(d, (xs2, bot))
    wire(d, (xs2, top), (20.0, top)); wire(d, (xs2, bot), (20.0, bot))
    d += elm.Capacitor().endpoints((20.0, top), (20.0, bot)).label("$C_2$", loc="bottom")
    dot(d, (20.0, top)); dot(d, (20.0, bot))
    wire(d, (20.0, top), (21.6, top)); wire(d, (20.0, bot), (21.6, bot))
    d += elm.SourceV().endpoints((21.6, bot), (21.6, top)).label("$V_2$", loc="bottom", ofst=0.3)
    save(d, "topo-dab.png")

print("done")
