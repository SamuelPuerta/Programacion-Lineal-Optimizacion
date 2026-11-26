"""Interfaz Streamlit: solo renderiza; la lógica está en modelo/simplex/grafico/sensibilidad."""
import json
import pandas as pd
import streamlit as st
from modelo import construir, desde_dict, SIMB
from ejemplos import EJEMPLOS
from simplex import resolver
from sensibilidad import sensibilidad
from grafico import grafico
from reporte import texto, pdf_bytes, tablero_filas

st.set_page_config(page_title="Programación Lineal – Gran M", layout="wide")
ss = st.session_state
cols = lambda n: [f"x{j+1}" for j in range(n)]


def cargar(d):
    n, m = len(d["c"]), len(d["b"])
    ss.n, ss.m, ss.opt = n, m, "Max" if d["max"] else "Min"
    ss.obj = pd.DataFrame([[str(v) for v in d["c"]]], columns=cols(n))
    ss.cons = pd.DataFrame([[*map(str, d["A"][i]), SIMB[d["sense"][i]], str(d["b"][i])] for i in range(m)],
                           columns=cols(n) + ["Sentido", "LD"])
    ss.ver = ss.get("ver", 0) + 1


def cb_ejemplo(): cargar(EJEMPLOS[ss.sel_ej])


def cb_archivo():
    f = ss.get("upl")
    if f is None: return
    try:
        pr, err = desde_dict(json.load(f))
    except Exception:
        pr, err = None, ["El archivo no es un JSON válido."]
    if err: ss.err_carga = err
    else: ss.err_carga = None; cargar(pr.to_dict())


if "n" not in ss: cargar(EJEMPLOS[next(iter(EJEMPLOS))])

st.title("Programación Lineal – Método de la Gran M")
with st.sidebar:
    st.header("Cargar problema")
    st.selectbox("Ejemplos del enunciado", list(EJEMPLOS), key="sel_ej")
    st.button("Cargar ejemplo", on_click=cb_ejemplo, key="btn_ej")
    st.file_uploader("Archivo JSON", type="json", key="upl")
    st.button("Cargar archivo", on_click=cb_archivo, key="btn_arch")
    for e in ss.get("err_carga") or []: st.error(e)

c1, c2, c3 = st.columns(3)
c1.number_input("Variables (n)", 1, 15, key="n")
c2.number_input("Restricciones (m)", 1, 15, key="m")
c3.radio("Objetivo", ["Max", "Min"], key="opt", horizontal=True)

cs = cols(ss.n)
ss.obj = ss.obj.reset_index(drop=True).reindex(index=[0], columns=cs, fill_value="0")
cc = ss.cons.reset_index(drop=True).reindex(index=range(ss.m), columns=cs + ["Sentido", "LD"], fill_value="0")
cc["Sentido"] = cc["Sentido"].where(cc["Sentido"].isin(["≤", "≥", "="]), "≤")
cc.index = [f"R{i+1}" for i in range(ss.m)]
key = f"{ss.get('ver', 0)}_{ss.n}_{ss.m}"
st.subheader("Función objetivo (coeficientes; admite fracciones como 2/5)")
obj = st.data_editor(ss.obj, key=f"obj_{key}", hide_index=True)
st.subheader("Restricciones (x ≥ 0)")
cons = st.data_editor(cc, key=f"cons_{key}",
                      column_config={"Sentido": st.column_config.SelectboxColumn("Sentido", options=["≤", "≥", "="], required=True)})
ss.obj, ss.cons = obj, cons

pr, errs = construir(ss.opt == "Max", [obj.iloc[0][c] for c in cs],
                     [[cons.iloc[i][c] for c in cs] for i in range(ss.m)],
                     [cons.iloc[i]["Sentido"] for i in range(ss.m)], [cons.iloc[i]["LD"] for i in range(ss.m)])
if errs:
    for e in errs: st.error(e)
    st.stop()
st.download_button("Guardar problema (JSON)", json.dumps(pr.to_dict(), indent=1), "problema.json", "application/json")

res = resolver(pr)
sens = sensibilidad(pr, res)
t1, t2, t3, t4 = st.tabs(["Solución", "Método gráfico", "Sensibilidad", "Exportar PDF"])

with t1:
    modo = st.radio("Modo de solución", ["Solución directa", "Paso a paso"], horizontal=True, key="modo_sol")
    if res["status"] == "infeasible": st.error("El problema no tiene solución factible.")
    elif res["status"] == "unbounded": st.warning("Solución no acotada: Z puede mejorar indefinidamente.")
    elif res["status"] == "error": st.error("No se pudo resolver el problema (demasiadas iteraciones).")
    else:
        st.success(f"Solución óptima: Z = {res['Z']}")
        st.dataframe(pd.DataFrame({"Variable": cs, "Valor": [str(v) for v in res["x"]]}), hide_index=True)
        st.dataframe(pd.DataFrame({"Restricción": [f"R{i+1}" for i in range(pr.m)],
                                   "Tipo": [t for t, _ in res["holguras"]],
                                   "Valor": [str(v) for _, v in res["holguras"]]}), hide_index=True)
        if res["multiple"]:
            alt = res["alt"]
            st.info("Soluciones óptimas múltiples: Z es igual en todo el segmento entre "
                    f"({', '.join(map(str, res['x']))}) y " +
                    (f"({', '.join(map(str, alt))})." if isinstance(alt, list) else "una dirección no acotada de óptimos."))
        if res["degenerate"]: st.info("Solución degenerada: hay una variable básica con valor 0 (o empate en la razón mínima).")
    if modo == "Paso a paso":
        st.markdown("#### Forma estándar")
        st.code("\n".join(res["estandar"]), language=None)
        if not pr.maximize: st.caption("Para Min, la fila Z' corresponde a Z' = -Z (el Z final se reporta ya corregido).")
        for stp in res["steps"]:
            st.markdown(f"#### {'Iteración ' + str(stp['k']) if stp['k'] else 'Tablero inicial'}"
                        + (" (final)" if stp["enter"] is None and stp["k"] else ""))
            h, r = tablero_filas(res, stp)
            st.dataframe(pd.DataFrame(r, columns=h), hide_index=True)
            st.markdown(stp["texto"])

with t2:
    fig, info = grafico(pr, res)
    if fig is None: st.info(info["mensaje"])
    else:
        if info["mensaje"]: st.warning(info["mensaje"])
        st.plotly_chart(fig, width="stretch")
        if info["vertices"]:
            st.dataframe(pd.DataFrame([(str(a), str(b), str(z)) for a, b, z in info["vertices"]],
                                      columns=["x1", "x2", "Z"]), hide_index=True)

with t3:
    if sens is None: st.info("El análisis de sensibilidad solo está disponible cuando hay solución óptima.")
    else:
        inf = lambda v, s: s if v is None else str(v)
        st.markdown("**Precios sombra y rango del lado derecho**")
        rows = []
        for i in range(pr.m):
            y = sens["sombra"][i]
            tx = ("Restricción no activa o con holgura: cambiar su LD no altera Z." if y == 0 else
                  f"Si el LD aumenta 1 unidad (dentro del rango), Z {'aumenta' if y > 0 else 'disminuye'} en {abs(y)}.")
            rows.append((f"R{i+1}", str(y), str(pr.b[i]), f"[{inf(sens['rango_b'][i][0], '-∞')}, {inf(sens['rango_b'][i][1], '+∞')}]", tx))
        st.dataframe(pd.DataFrame(rows, columns=["Restricción", "Precio sombra", "LD actual", "Rango LD", "Interpretación"]), hide_index=True)
        st.markdown("**Costos reducidos y rango de los coeficientes de Z**")
        rows = []
        for j in range(pr.n):
            r = sens["costos"][j]
            tx = ("Variable básica: costo reducido 0." if sens["basica"][j] else
                  f"Forzar 1 unidad de x{j+1} empeora Z en {abs(r)}." if r != 0 else
                  "Costo reducido 0: hay óptimos alternativos.")
            rows.append((f"x{j+1}", str(pr.c[j]), str(r), f"[{inf(sens['rango_c'][j][0], '-∞')}, {inf(sens['rango_c'][j][1], '+∞')}]", tx))
        st.dataframe(pd.DataFrame(rows, columns=["Variable", "c actual", "Costo reducido", "Rango c", "Interpretación"]), hide_index=True)

with t4:
    st.download_button("Descargar paso a paso (PDF)", pdf_bytes(texto(pr, res, sens)), "paso_a_paso.pdf", "application/pdf")
