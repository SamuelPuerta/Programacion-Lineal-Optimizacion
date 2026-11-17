"""Método gráfico (solo n = 2): región factible, vértices con Z y recta de isoutilidad."""
from fractions import Fraction as F
from math import atan2, ceil
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def _inter(l1, l2):
    a1, b1, c1 = l1; a2, b2, c2 = l2
    det = a1 * b2 - a2 * b1
    return None if det == 0 else ((c1 * b2 - c2 * b1) / det, (a1 * c2 - a2 * c1) / det)


def _ok(pt, cons):
    x, y = pt
    if x < 0 or y < 0: return False
    for a1, a2, s, b in cons:
        v = a1 * x + a2 * y
        if (s == "<=" and v > b) or (s == ">=" and v < b) or (s == "=" and v != b): return False
    return True


def _vertices(cons):
    lines = [(a1, a2, b) for a1, a2, s, b in cons] + [(F(1), F(0), F(0)), (F(0), F(1), F(0))]
    pts = set()
    for i in range(len(lines)):
        for j in range(i + 1, len(lines)):
            pt = _inter(lines[i], lines[j])
            if pt and _ok(pt, cons): pts.add(pt)
    return pts


def _f(v): return str(v) if v.denominator == 1 else f"{float(v):.3g}"


def grafico(p, res):
    if p.n != 2:
        return None, {"mensaje": f"El método gráfico no aplica: el problema tiene {p.n} variables (solo se grafica con 2)."}
    cons = [(p.A[i][0], p.A[i][1], p.sense[i], p.b[i]) for i in range(p.m)]
    V = _vertices(cons)
    info = {"vertices": [], "vacia": not V, "no_acotada": False, "mensaje": None}
    coords = [abs(v) for pt in V for v in pt]
    for a1, a2, s, b in cons:
        for a in (a1, a2):
            if a != 0 and b / a > 0: coords.append(b / a)
    L = F(max(2, ceil(float(max(coords + [F(1)])) * 1.3)))
    fig, ax = plt.subplots(figsize=(7, 6))
    xs = np.linspace(0, float(L), 200)
    for i, (a1, a2, s, b) in enumerate(cons):
        lbl = f"R{i+1}: {lin2(a1, a2)} {'≤' if s == '<=' else '≥' if s == '>=' else '='} {_f(b)}"
        if a2 != 0: ax.plot(xs, (float(b) - float(a1) * xs) / float(a2), label=lbl)
        elif a1 != 0: ax.axvline(float(b / a1), label=lbl, color=f"C{i}")
    if V:
        poly = _vertices(cons + [(F(1), F(0), "<=", L), (F(0), F(1), "<=", L)])
        pl = sorted(poly, key=lambda q: (atan2(float(q[1]) - sum(float(t[1]) for t in poly) / len(poly),
                                               float(q[0]) - sum(float(t[0]) for t in poly) / len(poly))))
        if len(pl) >= 3:
            ax.fill([float(a) for a, _ in pl], [float(b) for _, b in pl], alpha=0.3, color="tab:green", label="Región factible")
        info["no_acotada"] = any(q[0] == L or q[1] == L for q in poly)
        if info["no_acotada"]:
            info["mensaje"] = "La región factible es no acotada (se muestra recortada al borde del gráfico)."
        for q in sorted(V):
            z = p.c[0] * q[0] + p.c[1] * q[1]
            info["vertices"].append((q[0], q[1], z))
            ax.plot(float(q[0]), float(q[1]), "ko", ms=5)
            ax.annotate(f"({_f(q[0])}, {_f(q[1])})\nZ={_f(z)}", (float(q[0]), float(q[1])),
                        textcoords="offset points", xytext=(6, 6), fontsize=8)
    else:
        info["mensaje"] = "La región factible es vacía: el problema es infactible."
        ax.text(0.5, 0.5, "Región factible vacía", transform=ax.transAxes, ha="center", fontsize=14, color="red")
    if res["status"] == "optimal":
        Z, (c1, c2) = res["Z"], p.c
        pts = [res["x"]] + ([res["alt"]] if isinstance(res["alt"], list) else [])
        if c2 != 0: ax.plot(xs, (float(Z) - float(c1) * xs) / float(c2), "r--", lw=2, label=f"Isoutilidad Z = {_f(Z)}")
        elif c1 != 0: ax.axvline(float(Z / c1), color="r", ls="--", lw=2, label=f"Isoutilidad Z = {_f(Z)}")
        for q in pts: ax.plot(float(q[0]), float(q[1]), "r*", ms=15)
    elif res["status"] == "unbounded":
        info["mensaje"] = "Problema no acotado: Z crece sin límite dentro de la región no acotada."
    ax.set_xlim(0, float(L)); ax.set_ylim(0, float(L))
    ax.set_xlabel("x1"); ax.set_ylabel("x2"); ax.grid(alpha=0.3)
    ax.legend(fontsize=8, loc="upper right")
    ax.set_title(f"Método gráfico — {'Max' if p.maximize else 'Min'} Z = {lin2(*p.c)}")
    plt.tight_layout()
    return fig, info


def lin2(a, b):
    from simplex import lin
    return lin([a, b], ["x1", "x2"])
