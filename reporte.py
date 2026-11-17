"""Reporte en texto plano / PDF del paso a paso."""
from fpdf import FPDF


def _tabla(head, rows):
    w = [max(len(str(x)) for x in col) for col in zip(head, *rows)]
    f = lambda r: " | ".join(str(x).rjust(k) for x, k in zip(r, w))
    return [f(head), "-+-".join("-" * k for k in w)] + [f(r) for r in rows]


def tablero_filas(res, st):
    names = res["names"]
    head = ["Base"] + names + ["LD", "Razon"]
    rows = []
    for i, row in enumerate(st["T"]):
        r = [str(v) for v in row]
        if st["enter"] is not None and i == st["leave"]: r[st["enter"]] = f"[{r[st['enter']]}]"
        rz = "-" if not st["ratios"] or st["ratios"][i] is None else str(st["ratios"][i])
        rows.append([names[st["basis"][i]]] + r + [str(st["rhs"][i]), rz])
    rows.append(["Z'(zj-cj)"] + [str(v) for v in st["d"]] + [str(st["z"]), ""])
    return head, rows


def texto(p, res, sens):
    L = ["PROGRAMACION LINEAL - METODO DE LA GRAN M", ""]
    L += ["FORMA ESTANDAR"] + res["estandar"] + [""]
    for st in res["steps"]:
        L += [f"--- Tablero {st['k']} ---"] + _tabla(*tablero_filas(res, st)) + [st["texto"], ""]
    L.append(f"ESTADO: {res['status']}")
    if res["status"] == "optimal":
        L += [f"{nm} = {v}" for nm, v in zip(res["names"], res["x"])] + [f"Z = {res['Z']}"]
        L += [f"R{i+1}: {t} = {v}" for i, (t, v) in enumerate(res["holguras"])]
    if sens:
        L += ["", "SENSIBILIDAD"]
        L += [f"R{i+1}: precio sombra={s}, rango LD={r}" for i, (s, r) in enumerate(zip(sens["sombra"], sens["rango_b"]))]
        L += [f"x{j+1}: costo reducido={c}, rango c={r}" for j, (c, r) in enumerate(zip(sens["costos"], sens["rango_c"]))]
    return "\n".join(L).replace("≤", "<=").replace("≥", ">=")


def pdf_bytes(txt):
    pdf = FPDF(orientation="L")
    pdf.set_auto_page_break(True, 10); pdf.add_page(); pdf.set_font("Courier", size=7)
    for line in txt.split("\n"):
        pdf.cell(0, 3.4, line.encode("latin-1", "replace").decode("latin-1"), new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())
