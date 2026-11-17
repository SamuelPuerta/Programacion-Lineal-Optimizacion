"""Modelo del problema, validación de la entrada y (de)serialización JSON."""
from fractions import Fraction as F

SENT = {"≤": "<=", "≥": ">=", "=": "=", "<=": "<=", ">=": ">="}
SIMB = {"<=": "≤", ">=": "≥", "=": "="}
MAX_DIM = 15


class Problema:
    def __init__(self, maximize, c, A, sense, b):
        self.maximize, self.c, self.A, self.sense, self.b = maximize, c, A, sense, b

    @property
    def n(self): return len(self.c)

    @property
    def m(self): return len(self.b)

    def to_dict(self):
        return {"max": self.maximize, "c": [str(v) for v in self.c],
                "A": [[str(v) for v in r] for r in self.A],
                "sense": list(self.sense), "b": [str(v) for v in self.b]}


def _num(v, donde, errores):
    if v is None or str(v).strip() == "" or str(v).strip().lower() == "nan":
        errores.append(f"Campo vacío: {donde}.")
        return F(0)
    try:
        return F(str(v).strip().replace(",", "."))
    except (ValueError, ZeroDivisionError):
        errores.append(f"Valor no numérico en {donde}: '{v}'.")
        return F(0)


def construir(maximize, c, A, sent, b):
    """Valida y convierte. Devuelve (Problema | None, lista_de_errores)."""
    n, m = len(c), len(b)
    if n < 1 or m < 1:
        return None, ["Debe haber al menos 1 variable y 1 restricción."]
    if n > MAX_DIM or m > MAX_DIM:
        return None, [f"Máximo {MAX_DIM} variables y {MAX_DIM} restricciones."]
    if len(A) != m or len(sent) != m or any(len(r) != n for r in A):
        return None, ["Dimensiones inconsistentes: cada restricción debe tener "
                      f"{n} coeficientes y exactamente un signo y un lado derecho."]
    err = []
    cc = [_num(v, f"coeficiente de x{j+1} en la función objetivo", err) for j, v in enumerate(c)]
    AA = [[_num(v, f"restricción R{i+1}, coeficiente de x{j+1}", err) for j, v in enumerate(r)]
          for i, r in enumerate(A)]
    bb = [_num(v, f"lado derecho de R{i+1}", err) for i, v in enumerate(b)]
    ss = []
    for i, s in enumerate(sent):
        if str(s).strip() not in SENT:
            err.append(f"Signo inválido o vacío en R{i+1} (use ≤, ≥ o =).")
            ss.append("<=")
        else:
            ss.append(SENT[str(s).strip()])
    if err:
        return None, err
    return Problema(bool(maximize), cc, AA, ss, bb), []


def desde_dict(d):
    try:
        return construir(bool(d["max"]), d["c"], d["A"], d["sense"], d["b"])
    except (KeyError, TypeError):
        return None, ["El archivo no tiene el formato esperado (max, c, A, sense, b)."]
