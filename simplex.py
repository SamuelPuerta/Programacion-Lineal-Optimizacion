"""Método de la Gran M (tablero), implementación propia con fracciones exactas.

Cada costo es a + bM (clase BM) y se compara lexicográficamente (primero b, luego a),
así no se usa un M numérico. `resolver` NO imprime nada: devuelve la lista de pasos.
"""
from fractions import Fraction as F
from functools import total_ordering


def _c(x): return x if isinstance(x, BM) else BM(x)


@total_ordering
class BM:
    __slots__ = ("a", "b")

    def __init__(self, a=0, b=0): self.a, self.b = F(a), F(b)
    def __add__(s, o): o = _c(o); return BM(s.a + o.a, s.b + o.b)
    __radd__ = __add__
    def __sub__(s, o): o = _c(o); return BM(s.a - o.a, s.b - o.b)
    def __neg__(s): return BM(-s.a, -s.b)
    def __mul__(s, k): k = F(k); return BM(s.a * k, s.b * k)   # solo por escalares
    __rmul__ = __mul__
    def key(s): return (s.b, s.a)
    def __eq__(s, o): return s.key() == _c(o).key()
    def __lt__(s, o): return s.key() < _c(o).key()

    def __str__(s):
        if s.b == 0: return str(s.a)
        mt = "M" if abs(s.b) == 1 else f"{abs(s.b)}M"
        if s.a == 0: return ("-" if s.b < 0 else "") + mt
        return f"{s.a} {'-' if s.b < 0 else '+'} {mt}"


def _t(cf, nm, first):
    if cf == 0: return ""
    mag = abs(cf)
    num = nm if mag == 1 else (f"{mag}{nm}" if mag.denominator == 1 else f"({mag}){nm}")
    return ("-" if cf < 0 else "") + num if first else (" - " if cf < 0 else " + ") + num


def lin(coefs, names):
    s = ""
    for cf, nm in zip(coefs, names):
        s += _t(cf, nm, s == "")
    return s or "0"


def _pivot(S, r, e):
    T, rhs, d = S["T"], S["rhs"], S["d"]
    pv = T[r][e]
    T[r] = [v / pv for v in T[r]]
    rhs[r] = rhs[r] / pv
    for i in range(len(T)):
        if i != r and T[i][e] != 0:
            f = T[i][e]
            T[i] = [v - f * w for v, w in zip(T[i], T[r])]
            rhs[i] -= f * rhs[r]
    de = d[e]
    S["d"] = [dj - de * T[r][j] for j, dj in enumerate(d)]
    S["z"] = S["z"] - de * rhs[r]
    S["basis"][r] = e


def _snap(S):
    return {"T": [r[:] for r in S["T"]], "rhs": S["rhs"][:], "d": S["d"][:],
            "z": S["z"], "basis": S["basis"][:]}


def _copy(S): return _snap(S)


def _ratios(S, e):
    return [S["rhs"][i] / S["T"][i][e] if S["T"][i][e] > 0 else None for i in range(len(S["T"]))]


def resolver(p, max_iter=500):
    n, m = p.n, p.m
    names = [f"x{j+1}" for j in range(n)]
    kinds = ["x"] * n
    cint = [BM(v if p.maximize else -v) for v in p.c]
    rows, rhs, flipped, senses = [], [], [], []
    for i in range(m):
        a, bi, s = list(p.A[i]), p.b[i], p.sense[i]
        f = bi < 0
        if f:
            a, bi, s = [-v for v in a], -bi, {"<=": ">=", ">=": "<=", "=": "="}[s]
        rows.append(a); rhs.append(bi); flipped.append(f); senses.append(s)
    T = [r[:] for r in rows]

    def add(kind, i, coef):
        names.append(f"{kind}{i+1}"); kinds.append(kind)
        cint.append(BM(0, -1) if kind == "a" else BM(0))
        for r in range(m): T[r].append(F(coef) if r == i else F(0))
        return len(names) - 1

    basis = [None] * m
    for i in range(m):
        if senses[i] == "<=": basis[i] = add("s", i, 1)
        elif senses[i] == ">=": add("e", i, -1); basis[i] = add("a", i, 1)
        else: basis[i] = add("a", i, 1)
    N = len(names)
    init_basis = basis[:]
    art = [j for j in range(N) if kinds[j] == "a"]
    cB = [cint[b] for b in basis]
    d = [sum(cB[i] * T[i][j] for i in range(m)) - cint[j] for j in range(N)]
    z = sum(cB[i] * rhs[i] for i in range(m))
    S = {"T": T, "rhs": rhs, "d": d, "z": z, "basis": basis}

    # ---- forma estándar (texto)
    est = [f"{'Max' if p.maximize else 'Min'} Z = {lin(p.c, names[:n])}"]
    if not p.maximize:
        est.append(f"Se resuelve como maximización: Max Z' = -Z = {lin([-v for v in p.c], names[:n])}")
    obj = lin([cint[j].a for j in range(N) if kinds[j] != 'a'], [names[j] for j in range(N) if kinds[j] != 'a'])
    est.append("Con Gran M: Max Z' = " + obj + "".join(f" - M {names[j]}" for j in art))
    for i in range(m):
        nota = " (fila multiplicada por -1 porque el lado derecho era negativo)" if flipped[i] else ""
        est.append(f"R{i+1}: {lin(T[i], names)} = {rhs[i]}{nota}")
    est.append("Variables: " + ", ".join(
        f"{nm} ({'original' if k == 'x' else 'holgura' if k == 's' else 'exceso' if k == 'e' else 'artificial'})"
        for nm, k in zip(names, kinds)))

    steps, status, tie_seen, it = [], None, False, 0
    while True:
        st = _snap(S); st.update(k=it, enter=None, leave=None, ratios=None, pivot=None)
        neg = [j for j in range(N) if S["d"][j] < 0]
        if not neg:
            st["texto"] = "Todos los costos reducidos son ≥ 0: se alcanzó el óptimo."
            steps.append(st); break
        bland = it >= 30
        e = neg[0] if bland else min(neg, key=lambda j: (S["d"][j].key(), j))
        why = ("regla de Bland (para evitar ciclos)" if bland else
               "tiene el costo reducido más negativo" +
               (" (empate: se elige el de menor índice)" if sum(S["d"][j] == S["d"][e] for j in neg) > 1 else ""))
        rat = _ratios(S, e)
        st.update(enter=e, ratios=rat)
        if all(r is None for r in rat):
            st["texto"] = (f"Entra {names[e]} ({why}), pero su columna no tiene valores positivos: "
                           "no hay razón mínima, Z puede crecer sin límite.")
            steps.append(st); status = "unbounded"; break
        rmin = min(r for r in rat if r is not None)
        cands = [i for i, r in enumerate(rat) if r == rmin]
        r = min(cands, key=lambda i: S["basis"][i])
        tie = len(cands) > 1
        if tie or rmin == 0: tie_seen = True
        st.update(leave=r, pivot=S["T"][r][e])
        st["texto"] = (f"Entra {names[e]}: {why}. Razón mínima = {rmin} (fila de {names[S['basis'][r]]}), "
                       f"sale {names[S['basis'][r]]}. Pivote = {S['T'][r][e]}."
                       + (" Hay empate en la razón mínima → solución degenerada (se elige por regla de Bland)." if tie else ""))
        steps.append(st)
        _pivot(S, r, e); it += 1
        if it > max_iter: status = "error"; break

    val = [F(0)] * N
    for i, b in enumerate(S["basis"]): val[b] = S["rhs"][i]
    if status is None:
        status = "infeasible" if any(val[j] > 0 for j in art) else "optimal"
    elif status == "unbounded" and any(val[j] > 0 for j in art):
        # con artificiales positivas no se puede afirmar "no acotado": se verifica la factibilidad (Z = 0)
        from modelo import Problema
        if resolver(Problema(True, [F(0)] * n, p.A, p.sense, p.b))["status"] == "infeasible":
            status = "infeasible"
            steps[-1]["texto"] += " Como queda una variable artificial positiva, el problema en realidad es infactible."

    res = {"status": status, "names": names, "kinds": kinds, "steps": steps, "estandar": est,
           "init_basis": init_basis, "flipped": flipped, "final": _snap(S), "art": art,
           "multiple": False, "alt": None, "degenerate": False, "x": None, "Z": None, "holguras": None}
    if status != "optimal":
        return res
    x = val[:n]
    Z = sum(c * v for c, v in zip(p.c, x))
    hol = []
    for i in range(m):
        lhs = sum(a * v for a, v in zip(p.A[i], x))
        if p.sense[i] == "<=": hol.append(("holgura", p.b[i] - lhs))
        elif p.sense[i] == ">=": hol.append(("exceso", lhs - p.b[i]))
        else: hol.append(("igualdad", F(0)))
    res.update(x=x, Z=Z, holguras=hol,
               degenerate=tie_seen or any(v == 0 for v in S["rhs"]))
    # óptimos múltiples: variable no básica (no artificial) con costo reducido 0
    for j in range(N):
        if j not in S["basis"] and kinds[j] != "a" and S["d"][j] == 0:
            res["multiple"] = True
            rat = _ratios(S, j)
            if all(r is None for r in rat):
                res["alt"] = "rayo"
            else:
                S2 = _copy(S)
                rmin = min(r for r in rat if r is not None)
                r = min([i for i, v in enumerate(rat) if v == rmin], key=lambda i: S2["basis"][i])
                _pivot(S2, r, j)
                v2 = [F(0)] * N
                for i, b in enumerate(S2["basis"]): v2[b] = S2["rhs"][i]
                res["alt"] = v2[:n]
            break
    return res
