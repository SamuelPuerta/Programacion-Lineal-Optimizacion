"""Método gráfico interactivo (solo n = 2) con Plotly.

Devuelve una figura de Plotly con un control deslizante (línea de tiempo) que
reconstruye el resultado paso a paso: se añaden las restricciones una por una,
la región factible se va recortando, luego se marcan los vértices con su Z y
finalmente la recta de isoutilidad y el punto óptimo.

La figura usa fondo transparente y colores neutros para integrarse tanto en el
tema claro como en el oscuro de Streamlit.
"""
from fractions import Fraction as F
from math import atan2, ceil
import plotly.graph_objects as go

# Colores pensados para funcionar sobre fondo claro y oscuro
GRID = "rgba(128,128,128,0.25)"
ZERO = "rgba(130,130,130,0.85)"
VERTEX = "#8e44ad"
OPTIMAL = "#e74c3c"
REGION_FILL = "rgba(46, 204, 113, 0.28)"
REGION_LINE = "rgba(39, 174, 96, 0.95)"


def _inter(l1, l2):
    a1, b1, c1 = l1
    a2, b2, c2 = l2
    det = a1 * b2 - a2 * b1
    return None if det == 0 else ((c1 * b2 - c2 * b1) / det, (a1 * c2 - a2 * c1) / det)


def _ok(pt, cons):
    x, y = pt
    if x < 0 or y < 0:
        return False
    for a1, a2, s, b in cons:
        v = a1 * x + a2 * y
        if (s == "<=" and v > b) or (s == ">=" and v < b) or (s == "=" and v != b):
            return False
    return True


def _vertices(cons):
    lines = [(a1, a2, b) for a1, a2, s, b in cons] + [(F(1), F(0), F(0)), (F(0), F(1), F(0))]
    pts = set()
    for i in range(len(lines)):
        for j in range(i + 1, len(lines)):
            pt = _inter(lines[i], lines[j])
            if pt and _ok(pt, cons):
                pts.add(pt)
    return pts


def _f(v):
    return str(v) if v.denominator == 1 else f"{float(v):.3g}"


def lin2(a, b):
    from simplex import lin
    return lin([a, b], ["x1", "x2"])


def _line_endpoints(a1, a2, b, L):
    """Extremos del segmento a1*x1 + a2*x2 = b recortado a [0, L] x [0, L]."""
    fl_L = float(L)
    pts = []

    def add_point(x, y):
        if 0 <= x <= fl_L + 1e-9 and 0 <= y <= fl_L + 1e-9:
            for px, py in pts:
                if abs(px - x) < 1e-7 and abs(py - y) < 1e-7:
                    return
            pts.append((min(max(x, 0.0), fl_L), min(max(y, 0.0), fl_L)))

    if a2 != 0:
        add_point(0.0, float(b / a2))
        add_point(fl_L, float((b - a1 * L) / a2))
    if a1 != 0:
        add_point(float(b / a1), 0.0)
        add_point(float((b - a2 * L) / a1), fl_L)

    if len(pts) >= 2:
        return [pts[0][0], pts[1][0]], [pts[0][1], pts[1][1]]
    if len(pts) == 1:
        return [pts[0][0], pts[0][0]], [pts[0][1], pts[0][1]]
    return [], []


def _polygon(cons, L):
    """Polígono factible (ordenado angularmente) de un subconjunto de restricciones."""
    poly = _vertices(cons + [(F(1), F(0), "<=", L), (F(0), F(1), "<=", L)])
    if len(poly) < 3:
        return []
    cx = sum(float(t[0]) for t in poly) / len(poly)
    cy = sum(float(t[1]) for t in poly) / len(poly)
    return sorted(poly, key=lambda q: atan2(float(q[1]) - cy, float(q[0]) - cx))


def _closed_xy(pl):
    if not pl:
        return [], []
    xs = [float(q[0]) for q in pl]
    ys = [float(q[1]) for q in pl]
    return xs + [xs[0]], ys + [ys[0]]


def _label_pos(q, eps=1e-9):
    """Ubicación de la etiqueta según dónde está el vértice (evita solapamientos)."""
    x, y = float(q[0]), float(q[1])
    if abs(x) <= eps and y > eps:
        return "middle right"
    if abs(y) <= eps and x > eps:
        return "top center"
    return "top right"


def _view_bounds(V, cons, L):
    """Ventana de ejes ajustada a la región (con contexto de las restricciones cercanas).

    Evita el problema de usar el intercepto más lejano (p. ej. 100 cuando la
    región llega apenas a 50), que dejaba media gráfica vacía.
    """
    if not V:
        return float(L), float(L)
    vx = max(float(q[0]) for q in V)
    vy = max(float(q[1]) for q in V)
    xs, ys = [vx], [vy]
    thrx = max(vx, 1.0) * 1.6
    thry = max(vy, 1.0) * 1.6
    for a1, a2, s, b in cons:
        if a1 != 0:
            t = float(b / a1)
            if t > 0 and t <= thrx:
                xs.append(t)
        if a2 != 0:
            t = float(b / a2)
            if t > 0 and t <= thry:
                ys.append(t)
    # margen + piso mínimo para regiones degeneradas (puntos/segmentos)
    X = max(max(xs), 3.0) * 1.12
    Y = max(max(ys), 3.0) * 1.12
    return min(X, float(L) * 1.25), min(Y, float(L) * 1.25)


def grafico(p, res):
    """Figura Plotly interactiva con línea de tiempo. Devuelve (fig | None, info)."""
    if p.n != 2:
        return None, {"mensaje": f"El método gráfico no aplica: el problema tiene {p.n} variables (solo se grafica con 2)."}

    cons = [(p.A[i][0], p.A[i][1], p.sense[i], p.b[i]) for i in range(p.m)]
    V = _vertices(cons)
    info = {"vertices": [], "vacia": not V, "no_acotada": False, "mensaje": None}

    coords = [abs(v) for pt in V for v in pt]
    for a1, a2, s, b in cons:
        for a in (a1, a2):
            if a != 0 and b / a > 0:
                coords.append(b / a)
    L = F(max(2, ceil(float(max(coords + [F(1)])) * 1.3)))
    fl_L = float(L)

    palette = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
               "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"]
    obj_txt = f"{'Max' if p.maximize else 'Min'} Z = {lin2(*p.c)}"

    fig = go.Figure()
    n_cons = len(cons)
    line_idx, region_idx, vert_idx = [], [], []

    # ---- Trazas de restricciones
    for i, (a1, a2, s, b) in enumerate(cons):
        sg = "≤" if s == "<=" else ("≥" if s == ">=" else "=")
        name = f"R{i+1}: {lin2(a1, a2)} {sg} {_f(b)}"
        xs, ys = _line_endpoints(a1, a2, b, L)
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines", name=name,
            line=dict(color=palette[i % len(palette)], width=2.5),
            hoverinfo="name", showlegend=True,
        ))
        line_idx.append(len(fig.data) - 1)

    # ---- Regiones factibles progresivas (una por paso)
    for k in range(1, n_cons + 1):
        xs, ys = _closed_xy(_polygon(cons[:k], L))
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines", fill="toself",
            fillcolor=REGION_FILL, line=dict(color=REGION_LINE, width=1.5),
            name="Región factible", hoverinfo="skip", showlegend=False,
        ))
        region_idx.append(len(fig.data) - 1)

    # ---- Vértices, agrupados por posición para etiquetas limpias
    if V:
        poly_full = _polygon(cons, L)
        info["no_acotada"] = any(q[0] == L or q[1] == L for q in poly_full)
        if info["no_acotada"]:
            info["mensaje"] = "La región factible es no acotada (se muestra recortada al borde del gráfico)."
        for q in sorted(V):
            info["vertices"].append((q[0], q[1], p.c[0] * q[0] + p.c[1] * q[1]))
    else:
        info["mensaje"] = "La región factible es vacía: el problema es infactible."

    groups = {}
    for q in sorted(V):
        groups.setdefault(_label_pos(q), []).append(q)
    first_v = True
    for pos, qs in groups.items():
        fig.add_trace(go.Scatter(
            x=[float(q[0]) for q in qs],
            y=[float(q[1]) for q in qs],
            mode="markers+text",
            name="Vértices factibles",
            showlegend=first_v,
            legendgroup="vertices",
            marker=dict(size=10, color=VERTEX, symbol="circle", line=dict(color="white", width=1.5)),
            text=[f"({_f(q[0])}, {_f(q[1])})<br>Z={_f(p.c[0]*q[0] + p.c[1]*q[1])}" for q in qs],
            textposition=pos, textfont=dict(size=11),
            hoverinfo="text",
        ))
        vert_idx.append(len(fig.data) - 1)
        first_v = False

    # ---- Isoutilidad y punto óptimo
    iso_idx, opt_idx = None, None
    has_iso = res.get("status") == "optimal"
    if has_iso:
        Z = res["Z"]
        ixs, iys = _line_endpoints(p.c[0], p.c[1], Z, L)
        fig.add_trace(go.Scatter(
            x=ixs, y=iys, mode="lines", name=f"Isoutilidad Z = {_f(Z)}",
            line=dict(color=OPTIMAL, width=3, dash="dash"),
            hoverinfo="name", showlegend=True,
        ))
        iso_idx = len(fig.data) - 1
        pts = [res["x"]] + ([res["alt"]] if isinstance(res.get("alt"), list) else [])
        fig.add_trace(go.Scatter(
            x=[float(q[0]) for q in pts], y=[float(q[1]) for q in pts],
            mode="markers", name="Solución óptima",
            marker=dict(size=17, color=OPTIMAL, symbol="star", line=dict(color="white", width=1.5)),
            hovertext=[f"ÓPTIMO ({_f(q[0])}, {_f(q[1])}) Z*={_f(Z)}" for q in pts],
            hoverinfo="text", showlegend=True,
        ))
        opt_idx = len(fig.data) - 1
    elif res.get("status") == "unbounded":
        info["mensaje"] = "Problema no acotado: Z crece sin límite dentro de la región no acotada."

    total = len(fig.data)

    def vis(lines=(), regions=(), verts=(), extra=()):
        v = [False] * total
        for i in (*lines, *regions, *verts, *extra):
            v[i] = True
        return v

    # ---- Pasos de la línea de tiempo
    steps = []
    for k in range(1, n_cons + 1):
        steps.append((
            f"R1..R{k}",
            f"Se añade la restricción R{k}; la región factible se recorta",
            vis(lines=line_idx[:k], regions=[region_idx[k - 1]]),
        ))
    last_region = region_idx[-1] if region_idx else None
    final_regions = [last_region] if last_region is not None else []
    steps.append((
        "Vértices",
        "Vértices de la región factible, evaluando Z en cada uno",
        vis(lines=line_idx, regions=final_regions, verts=vert_idx),
    ))
    if has_iso:
        steps.append((
            "Óptimo",
            f"Recta de isoutilidad Z = {_f(res['Z'])} tangente en el óptimo",
            vis(lines=line_idx, regions=final_regions, verts=vert_idx, extra=[iso_idx, opt_idx]),
        ))
    elif V:
        steps.append(("Construcción final", "Construcción gráfica completa",
                      vis(lines=line_idx, regions=final_regions, verts=vert_idx)))

    slider_steps = [{
        "label": label,
        "method": "update",
        "args": [{"visible": v},
                 {"title.text": f"Método gráfico — {obj_txt}<br><sup>{subtitle}</sup>"}],
    } for label, subtitle, v in steps]

    # Estado inicial = último paso (si no, Plotly muestra todas las regiones apiladas)
    for tr, shown in zip(fig.data, steps[-1][2]):
        tr.visible = shown

    # Ventana de ejes: ajustada a la región; si es no acotada/infactible, se usa la caja L
    use_L = (not V) or info["no_acotada"] or res.get("status") == "unbounded"
    if use_L:
        viewx = viewy = fl_L
    else:
        viewx, viewy = _view_bounds(V, cons, L)

    fig.update_layout(
        title=dict(text=f"Método gráfico — {obj_txt}<br><sup>{steps[-1][1]}</sup>",
                   x=0.02, y=0.97, xanchor="left", font=dict(size=18)),
        xaxis=dict(title=dict(text="x1", font=dict(size=15)), range=[0, viewx],
                   zeroline=True, zerolinewidth=2, zerolinecolor=ZERO,
                   gridcolor=GRID, tickfont=dict(size=12)),
        yaxis=dict(title=dict(text="x2", font=dict(size=15)), range=[0, viewy],
                   zeroline=True, zerolinewidth=2, zerolinecolor=ZERO,
                   gridcolor=GRID, tickfont=dict(size=12)),
        sliders=[{
            "active": len(slider_steps) - 1,
            "currentvalue": {"prefix": "Paso: ", "visible": True, "xanchor": "right",
                             "font": {"size": 14}},
            "pad": {"b": 10, "t": 55}, "len": 0.95, "x": 0.025, "y": -0.2,
            "steps": slider_steps,
        }],
        legend=dict(x=1.01, y=1, xanchor="left", yanchor="top",
                    bgcolor="rgba(0,0,0,0)", bordercolor="rgba(128,128,128,0.4)",
                    borderwidth=1, font=dict(size=12)),
        hovermode="closest",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Arial, sans-serif"),
        height=700,
        margin=dict(l=70, r=30, t=90, b=120),
    )

    if not V:
        fig.add_annotation(
            text="Región factible vacía (Infactible)",
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
            font=dict(size=20, color=OPTIMAL),
        )

    return fig, info
