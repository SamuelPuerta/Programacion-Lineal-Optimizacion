"""Análisis de sensibilidad a partir del tablero final (B^-1 está en las columnas iniciales)."""


def sensibilidad(p, res):
    if res["status"] != "optimal":
        return None
    S, n, m = res["final"], p.n, p.m
    T, rhs, d, basis = S["T"], S["rhs"], S["d"], S["basis"]
    sg = 1 if p.maximize else -1
    neg = lambda v: None if v is None else -v
    sombra, rango_b = [], []
    for i in range(m):
        j0 = res["init_basis"][i]
        y = d[j0].a                       # dual de la fila (ya multiplicada por -1 si hubo cambio)
        fl = res["flipped"][i]
        sombra.append((-y if fl else y) * sg)
        lo = hi = None
        for r in range(m):
            be = T[r][j0]
            if be > 0:
                v = -rhs[r] / be; lo = v if lo is None else max(lo, v)
            elif be < 0:
                v = -rhs[r] / be; hi = v if hi is None else min(hi, v)
        bf = -p.b[i] if fl else p.b[i]
        l2 = None if lo is None else bf + lo
        h2 = None if hi is None else bf + hi
        rango_b.append((neg(h2), neg(l2)) if fl else (l2, h2))
    costos, rango_c = [], []
    for j in range(n):
        ci = p.c[j] if p.maximize else -p.c[j]
        if j in basis:
            r = basis.index(j)
            lo = hi = None
            for k in range(len(d)):
                if k in basis or res["kinds"][k] == "a" or d[k].b != 0: continue
                al = T[r][k]
                if al > 0:
                    v = -d[k].a / al; lo = v if lo is None else max(lo, v)
                elif al < 0:
                    v = -d[k].a / al; hi = v if hi is None else min(hi, v)
            costos.append(0)
        else:
            lo, hi = None, d[j].a
            costos.append(d[j].a * (-1 if p.maximize else 1))
        a = None if lo is None else ci + lo
        b = None if hi is None else ci + hi
        rango_c.append((a, b) if p.maximize else (neg(b), neg(a)))
    return {"sombra": sombra, "rango_b": rango_b, "costos": costos, "rango_c": rango_c,
            "basica": [j in basis for j in range(n)]}
