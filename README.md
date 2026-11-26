# Programación Lineal - Método de la Gran M

## Proyecto Final de Optimización

### Samuel Puerta, Juan Pablo Valencia, Guillermo Mejía.

App web con interfaz gráfica. El método (Gran M tabular, fracciones exactas) es propio; scipy solo se usa en `tests/` para verificar.

## Requisitos e instalación

(Python 3.10+ + Streamlit)

```
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Ejecución

```
streamlit run app.py
```

## Pruebas

```
python -m pytest -q tests
```

## Estructura

| Archivo           | Función                                               |
| ----------------- | ----------------------------------------------------- |
| `app.py`          | Interfaz (solo renderiza)                             |
| `modelo.py`       | Problema, validación de entrada, JSON                 |
| `simplex.py`      | Gran M; devuelve la lista de pasos (sin imprimir)     |
| `sensibilidad.py` | Precios sombra, costos reducidos, rangos de c y de LD |
| `grafico.py`      | Método gráfico interactivo (Plotly) con línea de tiempo (n = 2) |
| `reporte.py`      | Texto y PDF del paso a paso                           |
| `ejemplos.py`     | Los 7 problemas del enunciado                         |

## Método gráfico

Con 2 variables, la pestaña **Método gráfico** usa Plotly (interactivo: zoom,
paneo, tooltips). Un control deslizante de *línea de tiempo* reconstruye el
resultado paso a paso: se añaden las restricciones una por una, la región
factible se va recortando, luego se marcan los vértices con su `Z` y, si hay
óptimo, se traza la recta de isoutilidad y el punto óptimo.

## Dónde modificar

- Regla de entrada/salida de variables: bucle `while` en `simplex.resolver`.
- Textos de justificación: campo `texto` de cada paso.
- Nuevo método (p. ej. simplex revisado): crear función que devuelva el mismo dict y llamarla desde `app.py`.

Bonificaciones incluidas: fracciones exactas, exportar PDF, cargar/guardar JSON.
