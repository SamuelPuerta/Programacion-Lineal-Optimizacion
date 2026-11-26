import os, sys, random
from fractions import Fraction as F
import numpy as np
import pytest
from scipy.optimize import linprog
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from modelo import construir, desde_dict
from ejemplos import EJEMPLOS
from simplex import resolver
from sensibilidad import sensibilidad
from grafico import grafico
from reporte import texto, pdf_bytes

def P(i): 
    pr, e = desde_dict(list(EJEMPLOS.values())[i - 1]); assert not e; return pr

def test_1():
    r = resolver(P(1)); assert r["status"] == "optimal" and r["x"] == [42, 16] and r["Z"] == 3380
    assert r["holguras"][2][1] == 24   # restricción redundante x2<=40
def test_2():
    r = resolver(P(2)); assert r["x"] == [F(2, 5), F(9, 5)] and r["Z"] == F(17, 5)
    assert r["holguras"][1] == ("exceso", F(0)) or r["holguras"][1][1] >= 0
def test_3():
    r = resolver(P(3)); assert r["x"] == [0, 100, 230] and r["Z"] == 1350
    assert grafico(P(3), r)[0] is None and "no aplica" in grafico(P(3), r)[1]["mensaje"]
def test_4(): assert resolver(P(4))["status"] == "infeasible"
def test_5(): assert resolver(P(5))["status"] == "unbounded"
def test_6():
    r = resolver(P(6)); assert r["status"] == "optimal" and r["Z"] == 10 and r["multiple"]
    pts = {tuple(r["x"]), tuple(r["alt"])}; assert pts == {(0, F(5, 2)), (3, 1)}
def test_7():
    r = resolver(P(7)); assert r["x"] == [0, 2] and r["Z"] == 18 and r["degenerate"]
    assert 0 in r["final"]["rhs"]

def test_pasos_contenido():
    r = resolver(P(2)); assert any(a == "a" for a in r["kinds"]) and any("exceso" in l or "artificial" in l for l in r["estandar"])
    assert any(s["enter"] is not None and s["leave"] is not None and s["pivot"] is not None for s in r["steps"])

def test_validacion():
    assert construir(True, ["1", ""], [["1", "1"]], ["<="], ["3"])[1]            # vacío
    assert construir(True, ["1", "a"], [["1", "1"]], ["<="], ["3"])[1]           # no numérico
    assert construir(True, ["1", "1"], [["1"]], ["<="], ["3"])[1]                # dimensiones
    assert construir(True, ["1", "1"], [["1", "1"]], [None], ["3"])[1]           # sin signo
    assert not construir(True, ["1/2", "0,5"], [["1", "1"]], ["≥"], ["-3"])[1]   # fracción, coma, RHS negativo

def _rand(rng):
    n, m = rng.randint(2, 4), rng.randint(2, 4)
    c = [rng.randint(-3, 6) for _ in range(n)]
    A = [[rng.randint(-2, 5) for _ in range(n)] for _ in range(m)]
    s = [rng.choice(["<=", "<=", ">=", "="]) for _ in range(m)]
    b = [rng.randint(-4, 20) for _ in range(m)]
    return rng.random() < .5, c, A, s, b

def test_aleatorios_vs_scipy():
    rng = random.Random(7); cmp = 0
    for _ in range(300):
        mx, c, A, s, b = _rand(rng)
        pr, _ = construir(mx, c, A, s, b); r = resolver(pr)
        Aub, bub, Aeq, beq = [], [], [], []
        for row, sg, bi in zip(A, s, b):
            if sg == "<=": Aub.append(row); bub.append(bi)
            elif sg == ">=": Aub.append([-v for v in row]); bub.append(-bi)
            else: Aeq.append(row); beq.append(bi)
        o = linprog([-v if mx else v for v in c], A_ub=Aub or None, b_ub=bub or None, A_eq=Aeq or None, b_eq=beq or None, bounds=(0, None), method="highs")
        esp = {0: "optimal", 2: "infeasible", 3: "unbounded"}[o.status]
        assert r["status"] == esp, (mx, c, A, s, b)
        if esp == "optimal":
            assert abs(float(r["Z"]) - (-o.fun if mx else o.fun)) < 1e-7; cmp += 1
    assert cmp > 40

@pytest.mark.parametrize("i", [1, 2, 3, 6, 7])
def test_sensibilidad_exacta(i):
    pr = P(i); r = resolver(pr); s = sensibilidad(pr, r); eps = F(1, 100)
    for k in range(pr.m):
        lo, hi = s["rango_b"][k]
        for e in (eps, -eps):
            nb = pr.b[k] + e
            if (lo is None or nb >= lo) and (hi is None or nb <= hi):
                b2 = pr.b[:]; b2[k] = nb
                r2 = resolver(construir(pr.maximize, pr.c, pr.A, pr.sense, b2)[0])
                assert r2["Z"] - r["Z"] == s["sombra"][k] * e
    for j in range(pr.n):
        lo, hi = s["rango_c"][j]
        base = lambda cc: sum(a * b for a, b in zip(cc, r["x"]))
        for e in (eps, -eps):
            c2 = pr.c[:]; c2[j] += e
            r2 = resolver(construir(pr.maximize, c2, pr.A, pr.sense, pr.b)[0])
            dentro = (lo is None or c2[j] >= lo) and (hi is None or c2[j] <= hi)
            if dentro: assert r2["Z"] == base(c2)           # misma solución óptima sigue valiendo
            else:
                assert (r2["Z"] > base(c2)) if pr.maximize else (r2["Z"] < base(c2))
        # los extremos del rango están sobre el borde
    # costos reducidos y precios sombra contra scipy (problema 1, max)
    if i == 1:
        o = linprog([-50, -80], A_ub=[[2, 1], [1, 3], [0, 1]], b_ub=[100, 90, 40], method="highs")
        assert np.allclose([float(v) for v in s["sombra"]], -o.ineqlin.marginals)
        assert s["sombra"] == [F(2, 5) * 50 - F(80, 5) * 0 and s["sombra"][0], s["sombra"][1], 0]

def test_grafico_todos():
    for i in range(1, 8):
        pr = P(i); r = resolver(pr); fig, info = grafico(pr, r)
        if pr.n == 2:
            assert fig is not None
            if i == 1: assert len(info["vertices"]) == 4 and any(z == 3380 for *_, z in info["vertices"])
            if i == 4: assert info["vacia"]
            if i == 5: assert info["no_acotada"]
        else: assert fig is None

def test_grafico_plotly_timeline():
    import plotly.graph_objects as go
    for i in range(1, 8):
        pr = P(i); r = resolver(pr); fig, info = grafico(pr, r)
        if pr.n != 2:
            assert fig is None
            continue
        assert isinstance(fig, go.Figure)
        steps = fig.layout.sliders[0].steps
        ntraces = len(fig.data)
        # m pasos de restricciones + 1 de vértices + (1 óptimo | 1 final si hay región)
        extra = 1 if r.get("status") == "optimal" else (1 if info["vertices"] else 0)
        assert len(steps) == pr.m + 1 + extra, (i, len(steps))
        for s in steps:
            assert len(s.args[0]["visible"]) == ntraces
        # el paso final muestra todas las trazas salvo las regiones parciales intermedias
        assert sum(steps[-1].args[0]["visible"]) == ntraces - (pr.m - 1)
        assert steps[0].args[0]["visible"][0] is True       # primera restricción visible
        assert sum(steps[0].args[0]["visible"]) == 2        # solo R1 y su región
        assert fig.to_json()                                # serializa sin Fraction

def test_pdf_y_json():
    pr = P(2); r = resolver(pr); b = pdf_bytes(texto(pr, r, sensibilidad(pr, r))); assert b[:4] == b"%PDF"
    pr2, e = desde_dict(pr.to_dict()); assert not e and pr2.c == pr.c and pr2.b == pr.b and resolver(pr2)["Z"] == r["Z"]

def test_ui():
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(os.path.join(os.path.dirname(__file__), "..", "app.py"), default_timeout=60).run()
    assert not at.exception
    for nm in EJEMPLOS:
        at.selectbox(key="sel_ej").select(nm).run(); at.button(key="btn_ej").click().run()
        for modo in ("Paso a paso", "Solución directa"):
            at.radio(key="modo_sol").set_value(modo).run()
            assert not at.exception, nm
        msgs = [x.value for x in list(at.error) + list(at.warning) + list(at.info) + list(at.success)]
        if nm.startswith("4"): assert any("no tiene solución factible" in m for m in msgs)
        if nm.startswith("5"): assert any("no acotada" in m for m in msgs)
        if nm.startswith("6"): assert any("múltiples" in m for m in msgs)
        if nm.startswith("7"): assert any("degenerada" in m for m in msgs)
    at.number_input(key="n").set_value(3).run(); assert not at.exception   # agregar variable sin reiniciar
    at.number_input(key="m").set_value(2).run(); assert not at.exception   # quitar restricción
